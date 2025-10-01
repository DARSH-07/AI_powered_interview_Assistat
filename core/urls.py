from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # API endpoints
    path('api/upload-resume/', views.upload_resume, name='upload_resume'),
    path('api/update-candidate-info/', views.update_candidate_info, name='update_candidate_info'),
    path('api/start-interview/', views.start_interview, name='start_interview'),
    path('api/submit-answer/', views.submit_answer, name='submit_answer'),
    path('api/candidate/<uuid:candidate_id>/', views.get_candidate_details, name='candidate_details'),
    path('api/check-session/', views.check_session, name='check_session'),
]