from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

LEVEL_CHOICES = ['ilkokul', 'ortaokul', 'lise', 'universite']
GRADE_CHOICES  = [1, 2, 3, 4]


class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(150), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(20), nullable=False, default='student')

    # Sadece öğrenciler kullanır
    school_level = db.Column(db.String(20), nullable=True)   # ilkokul / ortaokul / lise / universite
    grade        = db.Column(db.Integer, nullable=True)       # 1 / 2 / 3 / 4

    @property
    def profile_complete(self):
        """Öğrencinin profili tamamlanmış mı?"""
        if self.role == 'student':
            return self.school_level is not None and self.grade is not None
        return True


class Exam(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    teacher_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    duration     = db.Column(db.Integer, nullable=False)      # saniye
    start_time   = db.Column(db.DateTime, nullable=False)
    end_time     = db.Column(db.DateTime, nullable=False)

    # Hedef kitle
    target_level = db.Column(db.String(20), nullable=False)   # ilkokul / ortaokul / lise / universite
    target_grade = db.Column(db.Integer, nullable=False)       # 1 / 2 / 3 / 4

    teacher   = db.relationship('User', backref='exams', foreign_keys=[teacher_id])
    questions = db.relationship('Question', backref='exam', lazy=True, cascade='all, delete-orphan')

    @property
    def is_active(self):
        now = datetime.now()
        return self.start_time <= now <= self.end_time

    @property
    def status(self):
        now = datetime.now()
        if now < self.start_time:
            return 'upcoming'
        elif now > self.end_time:
            return 'expired'
        return 'active'


class Question(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    exam_id        = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    text           = db.Column(db.Text, nullable=False)
    options_json   = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)


class Result(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    score   = db.Column(db.Float, nullable=False)

    user = db.relationship('User', backref='results')
    exam = db.relationship('Exam', backref='results')


class UserAnswer(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    result_id       = db.Column(db.Integer, db.ForeignKey('result.id'), nullable=False)
    question_id     = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_answer = db.Column(db.String(300), nullable=True)
    is_correct      = db.Column(db.Boolean, nullable=False)

    result   = db.relationship('Result', backref='answers')
    question = db.relationship('Question', backref='user_answers')