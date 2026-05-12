from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='student') # 'teacher' veya 'student'

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.Integer, default=3600)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id')) # Sınavı hazırlayan hoca
    questions = db.relationship('Question', backref='exam', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False) # FOREIGN KEY[cite: 1]
    text = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, nullable=False) # Seçenekleri JSON string olarak tutacağız[cite: 1]
    correct_answer = db.Column(db.String(200), nullable=False)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    score = db.Column(db.Float, nullable=False) # FLOAT tipinde puan[cite: 1]
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())