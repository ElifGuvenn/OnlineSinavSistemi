from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='student')
    results = db.relationship('Result', back_populates='user', lazy=True)

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.Integer, default=3600)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    questions = db.relationship('Question', backref='exam', lazy=True, cascade="all, delete-orphan")
    results = db.relationship('Result', back_populates='exam', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', back_populates='results')
    exam = db.relationship('Exam', back_populates='results')
    
    answers = db.relationship('UserAnswer', backref='result', lazy=True, cascade="all, delete-orphan")

class UserAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('result.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_answer = db.Column(db.String(200), nullable=True) # Öğrencinin seçtiği şık
    is_correct = db.Column(db.Boolean, nullable=False) # Doğru mu yanlış mı?
    
    question = db.relationship('Question')