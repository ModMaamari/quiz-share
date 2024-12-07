from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_migrate import Migrate
from datetime import datetime
import secrets
import logging
import os
from dotenv import load_dotenv
import secrets
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv(dotenv_path=".env", override=True)

# Initialize Flask app
app = Flask(__name__)

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///quiz_app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# Initialize mail after configuration
mail = Mail(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quizzes = db.relationship('Quiz', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Quiz(db.Model):
    id = db.Column(db.String(16), primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    min_participants = db.Column(db.Integer, nullable=False)
    exact_participants = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    questions = db.relationship('Question', backref='quiz', lazy=True)
    responses = db.relationship('Response', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(16), db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(16), db.ForeignKey('quiz.id'), nullable=False)
    participant_email = db.Column(db.String(120), nullable=False)
    answers = db.relationship('Answer', backref='response', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.String(500), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/quiz/'):
        return 'Quiz not found (404)', 404
    return render_template('index.html'), 404

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page if next_page else url_for('index'))
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    user_quizzes = Quiz.query.filter_by(author_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    return render_template('profile.html', user=current_user, quizzes=user_quizzes)

@app.route('/create_quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if request.method == 'POST':
        quiz_id = secrets.token_urlsafe(8)
        quiz = Quiz(
            id=quiz_id,
            title=request.form['title'],
            password=request.form['password'],
            min_participants=int(request.form['min_participants']),
            exact_participants=request.form.get('exact_participants') == 'true',
            author_id=current_user.id
        )
        
        db.session.add(quiz)
        
        questions = request.form.getlist('questions[]')
        for question_text in questions:
            question = Question(quiz_id=quiz_id, question_text=question_text)
            db.session.add(question)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'quiz_id': quiz_id,
            'quiz_url': url_for('take_quiz', quiz_id=quiz_id, _external=True)
        })
    
    return render_template('create_quiz.html')

def send_results(quiz, recipient_emails=None):
    """
    Send quiz results via email.
    If recipient_emails is None, send to all participants.
    If recipient_emails is provided, send only to those emails.
    """
    if recipient_emails is None:
        recipient_emails = [response.participant_email for response in quiz.responses]
    
    # Create HTML email content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .quiz-title {{ color: #2c3e50; margin-bottom: 20px; }}
            .question {{ margin-bottom: 30px; background: #f8f9fa; padding: 15px; border-radius: 5px; }}
            .question-text {{ color: #2c3e50; font-weight: bold; margin-bottom: 15px; }}
            .answers {{ margin-left: 20px; }}
            .answer {{ margin-bottom: 10px; padding: 8px; border-left: 3px solid #3498db; }}
            .participant {{ color: #666; font-style: italic; }}
            .no-answer {{ color: #999; font-style: italic; }}
        </style>
    </head>
    <body>
        <h1 class="quiz-title">{quiz.title} - Results</h1>
        <p>Here are all questions and responses from all participants:</p>
    """
    
    # Get all responses
    responses = Response.query.filter_by(quiz_id=quiz.id).all()
    
    # Group answers by question
    for question in quiz.questions:
        html_content += f'<div class="question"><div class="question-text">Question: {question.question_text}</div><div class="answers">'
        
        # For each participant, show their answer or "No answer provided"
        for response in responses:
            answer = Answer.query.filter_by(
                response_id=response.id,
                question_id=question.id
            ).first()
            
            html_content += f'<div class="answer"><span class="participant">{response.participant_email}:</span><br>'
            if answer:
                html_content += f'{answer.answer_text}'
            else:
                html_content += f'<span class="no-answer">No answer provided</span>'
            html_content += '</div>'
        
        html_content += '</div></div>'
    
    html_content += """
        <p>Thank you for participating!</p>
    </body>
    </html>
    """
    
    # Create and send email
    msg = Message(
        f'Quiz Results: {quiz.title}',
        sender=app.config['MAIL_USERNAME'],
        recipients=recipient_emails,
        html=html_content
    )
    
    try:
        mail.send(msg)
    except Exception as e:
        app.logger.error(f'Failed to send email: {str(e)}')
        raise

@app.route('/quiz/<quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash('Quiz not found. Please check the quiz ID and try again.', 'error')
        return redirect(url_for('index'))

    if not quiz.is_active:
        flash('This quiz is no longer accepting responses as it has reached its maximum number of participants.')
        return render_template('quiz.html', quiz=quiz)

    if request.method == 'POST':
        # Handle password verification
        if not session.get('quiz_' + quiz_id + '_authenticated'):
            if request.form.get('password') == quiz.password:
                session['quiz_' + quiz_id + '_authenticated'] = True
                return render_template('quiz.html', quiz=quiz)
            else:
                flash('Incorrect password. Please try again.', 'error')
                return render_template('quiz.html', quiz=quiz)

        # Handle quiz submission
        email = request.form.get('email')
        
        # Check if email has already submitted
        if Response.query.filter_by(quiz_id=quiz_id, participant_email=email).first():
            flash('You have already submitted answers for this quiz.', 'error')
            return render_template('quiz.html', quiz=quiz)

        # Create response
        response = Response(quiz_id=quiz_id, participant_email=email)
        db.session.add(response)
        db.session.commit()  # Commit to get the response.id

        # Add answers
        for question in quiz.questions:
            answer_text = request.form.get(f'answer_{question.id}', '').strip()
            if answer_text:  # Only add non-empty answers
                answer = Answer(
                    response_id=response.id,
                    question_id=question.id,
                    answer_text=answer_text
                )
                db.session.add(answer)

        db.session.commit()

        response_count = len(quiz.responses)
        
        # Check if we should send results
        if quiz.exact_participants and response_count >= quiz.min_participants:
            # If exact participants reached, close quiz and send to all
            quiz.is_active = False
            db.session.commit()
            send_results(quiz)  # Send to all participants
            flash('Thank you for your submission! The quiz has reached its required number of participants. Results have been sent to all participants.')
        elif not quiz.exact_participants:
            if response_count == quiz.min_participants:
                # First time reaching min_participants, send to all
                send_results(quiz)
                flash('Thank you for your submission! Results have been sent to all participants.')
            elif response_count > quiz.min_participants:
                # Beyond min_participants, only send to current participant
                send_results(quiz, [email])
                flash('Thank you for your submission! The results have been sent to your email.')
        else:
            flash('Thank you for your submission! Results will be sent once the required number of participants is reached.')
        
        return redirect(url_for('index'))

    return render_template('quiz.html', quiz=quiz)

@app.route('/delete_quiz/<string:quiz_id>', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if the current user owns the quiz
    if quiz.author_id != current_user.id:
        flash('You do not have permission to delete this quiz.', 'error')
        return redirect(url_for('profile'))
    
    try:
        # First delete all answers associated with the quiz's responses
        for response in quiz.responses:
            Answer.query.filter_by(response_id=response.id).delete()
        
        # Then delete all responses
        Response.query.filter_by(quiz_id=quiz_id).delete()
        
        # Delete all questions
        Question.query.filter_by(quiz_id=quiz_id).delete()
        
        # Finally delete the quiz
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the quiz.', 'error')
        app.logger.error(f"Error deleting quiz {quiz_id}: {str(e)}")
    
    return redirect(url_for('profile'))

@app.route('/delete_all_quizzes', methods=['POST'])
@login_required
def delete_all_quizzes():
    password = request.form.get('password')
    
    # Verify user's password
    if not current_user.check_password(password):
        flash('Incorrect password. Please try again.', 'error')
        return redirect(url_for('profile'))
    
    try:
        # Get all quiz IDs for the current user
        quiz_ids = [quiz.id for quiz in current_user.quizzes]
        
        if quiz_ids:
            # First delete all answers
            for response in Response.query.filter(Response.quiz_id.in_(quiz_ids)).all():
                Answer.query.filter_by(response_id=response.id).delete()
            
            # Then delete all responses
            Response.query.filter(Response.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
            
            # Delete all questions
            Question.query.filter(Question.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
            
            # Finally delete all quizzes
            Quiz.query.filter_by(author_id=current_user.id).delete()
            
        db.session.commit()
        flash('All quizzes have been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting quizzes.', 'error')
        app.logger.error(f"Error deleting all quizzes for user {current_user.id}: {str(e)}")
    
    return redirect(url_for('profile'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Only creates tables if they don't exist
    app.run(debug=True)
