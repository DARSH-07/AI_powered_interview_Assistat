from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import Candidate, InterviewSession, Question, ChatMessage
from .utils import parse_resume, generate_question, evaluate_answer, generate_final_summary
import json
import logging
import uuid

logger = logging.getLogger(__name__)


def index(request):
    """Main page with tabs for interview and dashboard"""
    return render(request, 'interview.html')


def dashboard(request):
    """Dashboard view for interviewers"""
    candidates = Candidate.objects.all().order_by('-total_score', '-created_at')
    return render(request, 'dashboard.html', {'candidates': candidates})


@csrf_exempt
@require_http_methods(["POST"])
def upload_resume(request):
    """Handle resume upload and parsing"""
    try:
        if 'resume' not in request.FILES:
            return JsonResponse({'error': 'No resume file provided'}, status=400)
        
        resume_file = request.FILES['resume']
        
        # Validate file size (5MB limit)
        if resume_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Maximum size is 5MB.'}, status=400)
        
        # Create candidate
        candidate = Candidate.objects.create(resume=resume_file)
        
        # Parse resume to extract information
        try:
            parsed_data = parse_resume(resume_file)
            candidate.name = parsed_data.get('name', '')
            candidate.email = parsed_data.get('email', '')
            candidate.phone = parsed_data.get('phone', '')
            candidate.save()
        except Exception as e:
            logger.error(f"Resume parsing failed: {str(e)}")
            # Continue without parsed data
        
        # Create interview session
        session = InterviewSession.objects.create(candidate=candidate)
        
        # Store candidate ID in session for recovery
        request.session['candidate_id'] = str(candidate.id)
        
        return JsonResponse({
            'success': True,
            'candidate_id': str(candidate.id),
            'parsed_data': {
                'name': candidate.name,
                'email': candidate.email,
                'phone': candidate.phone,
            }
        })
        
    except Exception as e:
        logger.error(f"Resume upload failed: {str(e)}")
        return JsonResponse({'error': 'Upload failed. Please try again.'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_candidate_info(request):
    """Update missing candidate information"""
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        
        if not candidate_id:
            return JsonResponse({'error': 'Candidate ID required'}, status=400)
        
        candidate = get_object_or_404(Candidate, id=candidate_id)
        
        # Update provided information
        if data.get('name'):
            candidate.name = data['name']
        if data.get('email'):
            candidate.email = data['email']
        if data.get('phone'):
            candidate.phone = data['phone']
        
        candidate.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Update candidate info failed: {str(e)}")
        return JsonResponse({'error': 'Update failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_interview(request):
    """Start the interview process"""
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        
        if not candidate_id:
            return JsonResponse({'error': 'Candidate ID required'}, status=400)
        
        candidate = get_object_or_404(Candidate, id=candidate_id)
        session = get_object_or_404(InterviewSession, candidate=candidate)
        
        with transaction.atomic():
            # Update session status
            session.is_active = True
            session.started_at = timezone.now()
            session.current_question_number = 1
            session.save()
            
            # Update candidate status
            candidate.interview_status = 'in_progress'
            candidate.save()
            
            # Generate first question
            question_data = generate_question(1, 'easy')
            question = Question.objects.create(
                session=session,
                question_number=1,
                difficulty='easy',
                question_text=question_data['question'],
                time_allocated=20  # 20 seconds for easy questions
            )
            
            # Create system message
            ChatMessage.objects.create(
                session=session,
                message_type='system',
                content='Interview started. You will be asked 6 questions: 2 Easy, 2 Medium, 2 Hard.'
            )
            
            # Create question message
            ChatMessage.objects.create(
                session=session,
                message_type='question',
                content=question_data['question'],
                metadata={'question_number': 1, 'time_allocated': 20}
            )
        
        return JsonResponse({
            'success': True,
            'question': question_data['question'],
            'question_number': 1,
            'time_allocated': 20,
            'session_id': session.id
        })
        
    except Exception as e:
        logger.error(f"Start interview failed: {str(e)}")
        return JsonResponse({'error': 'Failed to start interview'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def submit_answer(request):
    """Submit answer and get next question"""
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        answer_text = data.get('answer', '')
        time_taken = data.get('time_taken', 0)
        
        if not candidate_id:
            return JsonResponse({'error': 'Candidate ID required'}, status=400)
        
        candidate = get_object_or_404(Candidate, id=candidate_id)
        session = get_object_or_404(InterviewSession, candidate=candidate)
        
        with transaction.atomic():
            # Get current question
            current_question = Question.objects.filter(
                session=session,
                question_number=session.current_question_number
            ).first()
            
            if not current_question:
                return JsonResponse({'error': 'No active question found'}, status=404)
            
            # Update question with answer
            current_question.answer_text = answer_text
            current_question.time_taken = time_taken
            current_question.answered_at = timezone.now()
            
            # Evaluate answer using AI
            try:
                evaluation = evaluate_answer(current_question.question_text, answer_text, current_question.difficulty)
                current_question.score = evaluation.get('score', 0)
                current_question.ai_feedback = evaluation.get('feedback', '')
            except Exception as e:
                logger.error(f"Answer evaluation failed: {str(e)}")
                current_question.score = 0
                current_question.ai_feedback = 'Evaluation failed'
            
            current_question.save()
            
            # Create answer message
            ChatMessage.objects.create(
                session=session,
                message_type='answer',
                content=answer_text,
                metadata={'question_number': session.current_question_number, 'score': current_question.score}
            )
            
            # Check if interview is complete
            if session.current_question_number >= 6:
                # Complete interview
                session.is_active = False
                session.completed_at = timezone.now()
                candidate.interview_status = 'completed'
                
                # Calculate total score
                total_score = session.questions.aggregate(
                    total=models.Sum('score')
                )['total'] or 0
                candidate.total_score = total_score
                
                # Generate final summary
                try:
                    questions_and_answers = list(session.questions.all().values(
                        'question_text', 'answer_text', 'score', 'difficulty'
                    ))
                    summary = generate_final_summary(questions_and_answers, total_score)
                    candidate.ai_summary = summary
                except Exception as e:
                    logger.error(f"Summary generation failed: {str(e)}")
                    candidate.ai_summary = 'Summary generation failed'
                
                session.save()
                candidate.save()
                
                # Create completion message
                ChatMessage.objects.create(
                    session=session,
                    message_type='system',
                    content=f'Interview completed! Your total score: {total_score:.1f}/60'
                )
                
                return JsonResponse({
                    'success': True,
                    'interview_completed': True,
                    'total_score': total_score,
                    'summary': candidate.ai_summary
                })
            
            else:
                # Generate next question
                session.current_question_number += 1
                next_question_num = session.current_question_number
                
                # Determine difficulty and time
                if next_question_num <= 2:
                    difficulty = 'easy'
                    time_allocated = 20
                elif next_question_num <= 4:
                    difficulty = 'medium'
                    time_allocated = 60
                else:
                    difficulty = 'hard'
                    time_allocated = 120
                
                # Generate question
                question_data = generate_question(next_question_num, difficulty)
                next_question = Question.objects.create(
                    session=session,
                    question_number=next_question_num,
                    difficulty=difficulty,
                    question_text=question_data['question'],
                    time_allocated=time_allocated
                )
                
                session.save()
                
                # Create question message
                ChatMessage.objects.create(
                    session=session,
                    message_type='question',
                    content=question_data['question'],
                    metadata={'question_number': next_question_num, 'time_allocated': time_allocated}
                )
                
                return JsonResponse({
                    'success': True,
                    'next_question': question_data['question'],
                    'question_number': next_question_num,
                    'time_allocated': time_allocated,
                    'current_score': current_question.score
                })
        
    except Exception as e:
        logger.error(f"Submit answer failed: {str(e)}")
        return JsonResponse({'error': 'Failed to submit answer'}, status=500)


def get_candidate_details(request, candidate_id):
    """Get detailed candidate information for dashboard"""
    try:
        candidate = get_object_or_404(Candidate, id=candidate_id)
        
        # Get interview session and questions
        try:
            session = candidate.session
            questions = list(session.questions.all().values(
                'question_number', 'difficulty', 'question_text', 
                'answer_text', 'score', 'time_taken', 'time_allocated'
            ))
            messages = list(session.messages.all().values(
                'message_type', 'content', 'timestamp'
            ))
        except InterviewSession.DoesNotExist:
            questions = []
            messages = []
        
        return JsonResponse({
            'candidate': {
                'id': str(candidate.id),
                'name': candidate.name,
                'email': candidate.email,
                'phone': candidate.phone,
                'interview_status': candidate.interview_status,
                'total_score': candidate.total_score,
                'ai_summary': candidate.ai_summary,
                'created_at': candidate.created_at.isoformat(),
            },
            'questions': questions,
            'chat_history': messages
        })
        
    except Exception as e:
        logger.error(f"Get candidate details failed: {str(e)}")
        return JsonResponse({'error': 'Failed to get candidate details'}, status=500)


def check_session(request):
    """Check for existing session to enable recovery"""
    candidate_id = request.session.get('candidate_id')
    
    if candidate_id:
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            if candidate.interview_status in ['pending', 'in_progress', 'paused']:
                try:
                    session = candidate.session
                    current_question = None
                    if session.current_question_number > 0:
                        current_question = session.questions.filter(
                            question_number=session.current_question_number
                        ).first()
                    
                    return JsonResponse({
                        'has_session': True,
                        'candidate': {
                            'id': str(candidate.id),
                            'name': candidate.name,
                            'email': candidate.email,
                            'phone': candidate.phone,
                            'interview_status': candidate.interview_status,
                        },
                        'current_question_number': session.current_question_number,
                        'current_question': current_question.question_text if current_question else None,
                        'time_allocated': current_question.time_allocated if current_question else None,
                    })
                except InterviewSession.DoesNotExist:
                    pass
        except Candidate.DoesNotExist:
            pass
    
    return JsonResponse({'has_session': False})