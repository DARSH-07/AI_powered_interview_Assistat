import io
import logging
import re
import google.generativeai as genai
from django.conf import settings
from PyPDF2 import PdfReader
from docx import Document
import json

logger = logging.getLogger(__name__)

# Configure Gemini AI
genai.configure(api_key=settings.GEMINI_API_KEY)


def parse_resume(file_obj):
    """
    Parse resume file to extract candidate information
    """
    try:
        file_content = ""
        file_extension = file_obj.name.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            file_content = extract_text_from_pdf(file_obj)
        elif file_extension == 'docx':
            file_content = extract_text_from_docx(file_obj)
        else:
            raise ValueError("Unsupported file format")
        
        if not file_content.strip():
            raise ValueError("Could not extract text from file")
        
        # Extract information using regex patterns
        extracted_data = {
            'name': extract_name(file_content),
            'email': extract_email(file_content),
            'phone': extract_phone(file_content)
        }
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Resume parsing error: {str(e)}")
        raise e


def extract_text_from_pdf(file_obj):
    """Extract text from PDF file"""
    try:
        # Reset file pointer
        file_obj.seek(0)
        
        reader = PdfReader(file_obj)
        text = ""
        
        for page in reader.pages:
            text += page.extract_text()
        
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        return ""


def extract_text_from_docx(file_obj):
    """Extract text from DOCX file"""
    try:
        # Reset file pointer
        file_obj.seek(0)
        
        doc = Document(file_obj)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text
    except Exception as e:
        logger.error(f"DOCX extraction error: {str(e)}")
        return ""


def extract_name(text):
    """Extract name from resume text"""
    try:
        # Simple name extraction - first line or after "Name:" keyword
        lines = text.strip().split('\n')
        
        # Look for name patterns
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and not any(keyword in line.lower() for keyword in ['email', 'phone', 'address', '@']):
                # Remove common titles
                line = re.sub(r'^(Mr\.?|Ms\.?|Mrs\.?|Dr\.?)\s+', '', line, flags=re.IGNORECASE)
                if len(line.split()) >= 2 and len(line) < 50:
                    return line
        
        return ""
    except:
        return ""


def extract_email(text):
    """Extract email from resume text"""
    try:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else ""
    except:
        return ""


def extract_phone(text):
    """Extract phone number from resume text"""
    try:
        # Various phone patterns
        patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'\+?[0-9]{1,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}',
            r'\b[0-9]{10}\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    return ''.join(matches[0])
                return matches[0]
        
        return ""
    except:
        return ""


def generate_question(question_number, difficulty):
    """
    Generate interview question using Gemini AI
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Create context based on question number and difficulty
        context = f"""
        You are conducting a technical interview for a Full Stack Developer position (React/Node.js).
        Generate question #{question_number} with {difficulty} difficulty level.
        
        Question Guidelines:
        - Easy (20 seconds): Basic concepts, definitions, simple syntax
        - Medium (60 seconds): Problem-solving, code explanation, best practices
        - Hard (120 seconds): Complex scenarios, architecture decisions, optimization
        
        Topics to cover: JavaScript, React, Node.js, databases, APIs, system design, web development fundamentals.
        
        Return ONLY the question text without any additional formatting or explanations.
        """
        
        response = model.generate_content(context)
        question_text = response.text.strip()
        
        return {
            'question': question_text,
            'difficulty': difficulty,
            'question_number': question_number
        }
        
    except Exception as e:
        logger.error(f"Question generation error: {str(e)}")
        # Fallback questions
        fallback_questions = {
            'easy': [
                "What is the difference between let, const, and var in JavaScript?",
                "Explain what React components are and their purpose.",
                "What is the purpose of package.json in a Node.js project?",
            ],
            'medium': [
                "How would you handle state management in a React application? Explain different approaches.",
                "Describe the event loop in Node.js and how it handles asynchronous operations.",
                "What are REST APIs and what makes an API RESTful?",
            ],
            'hard': [
                "Design a system architecture for a social media application. Consider scalability and performance.",
                "Explain how you would implement authentication and authorization in a full-stack application.",
                "How would you optimize a React application for performance? Discuss various techniques.",
            ]
        }
        
        questions = fallback_questions.get(difficulty, fallback_questions['easy'])
        question_text = questions[(question_number - 1) % len(questions)]
        
        return {
            'question': question_text,
            'difficulty': difficulty,
            'question_number': question_number
        }


def evaluate_answer(question, answer, difficulty):
    """
    Evaluate candidate's answer using Gemini AI
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Scoring criteria based on difficulty
        max_scores = {'easy': 10, 'medium': 10, 'hard': 10}
        max_score = max_scores[difficulty]
        
        context = f"""
        Evaluate this technical interview answer for a Full Stack Developer position.
        
        Question ({difficulty} difficulty): {question}
        Candidate's Answer: {answer}
        
        Provide evaluation in this JSON format:
        {{
            "score": <number between 0 and {max_score}>,
            "feedback": "<brief constructive feedback>"
        }}
        
        Scoring criteria:
        - Technical accuracy (40%)
        - Completeness of answer (30%)  
        - Clarity and communication (30%)
        
        Be fair but thorough in your evaluation.
        """
        
        response = model.generate_content(context)
        
        try:
            # Extract JSON from response
            result_text = response.text.strip()
            # Try to find JSON in the response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                result = json.loads(json_text)
                
                # Validate score range
                score = float(result.get('score', 0))
                score = max(0, min(score, max_score))
                
                return {
                    'score': score,
                    'feedback': result.get('feedback', 'No feedback provided')
                }
        except:
            pass
        
        # Fallback scoring based on answer length and keywords
        score = 0
        if answer.strip():
            score = min(max_score * 0.3, len(answer.split()) * 0.1)
            if any(keyword in answer.lower() for keyword in ['react', 'javascript', 'node', 'api', 'database']):
                score += max_score * 0.2
        
        return {
            'score': round(score, 1),
            'feedback': 'Answer received and evaluated.'
        }
        
    except Exception as e:
        logger.error(f"Answer evaluation error: {str(e)}")
        return {
            'score': 0,
            'feedback': 'Evaluation failed'
        }


def generate_final_summary(questions_and_answers, total_score):
    """
    Generate final AI summary of the interview
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Prepare interview data
        interview_data = ""
        for qa in questions_and_answers:
            interview_data += f"""
            Q: {qa['question_text']} ({qa['difficulty']})
            A: {qa['answer_text']}
            Score: {qa['score']}/10
            
            """
        
        context = f"""
        Generate a comprehensive interview summary for this Full Stack Developer candidate.
        
        Interview Results:
        Total Score: {total_score}/60
        
        {interview_data}
        
        Provide a summary covering:
        1. Overall performance assessment
        2. Technical strengths demonstrated
        3. Areas for improvement
        4. Recommendation (Hire/No Hire/Further Interview)
        
        Keep it professional, constructive, and concise (200-300 words).
        """
        
        response = model.generate_content(context)
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        
        # Fallback summary
        performance_level = "Poor"
        if total_score >= 45:
            performance_level = "Excellent"
        elif total_score >= 35:
            performance_level = "Good"
        elif total_score >= 25:
            performance_level = "Average"
        elif total_score >= 15:
            performance_level = "Below Average"
        
        return f"""
        Interview Summary:
        
        Overall Performance: {performance_level} ({total_score}/60 points)
        
        The candidate completed all 6 questions across easy, medium, and hard difficulty levels.
        Based on the responses provided, the candidate demonstrated varying levels of technical knowledge.
        
        Total Score Breakdown:
        - Easy Questions (2): Focus on fundamental concepts
        - Medium Questions (2): Problem-solving abilities  
        - Hard Questions (2): Advanced technical skills
        
        Recommendation: {"Hire" if total_score >= 35 else "Further evaluation recommended" if total_score >= 25 else "No hire"}
        
        Note: This is an automated summary. Human review recommended for final hiring decisions.
        """