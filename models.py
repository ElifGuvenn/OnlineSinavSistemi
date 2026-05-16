from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Öğretmen - Öğrenci many-to-many ilişki tablosu
teacher_student = db.Table('teacher_student',
    db.Column('teacher_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20), nullable=False, default='student')

    # Öğretmenin sorumlu olduğu öğrenciler (sadece teacher rolü kullanır)
    students = db.relationship(
        'User',
        secondary=teacher_student,
        primaryjoin=(teacher_student.c.teacher_id == id),
        secondaryjoin=(teacher_student.c.student_id == id),
        backref='teachers'
    )


class Exam(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    duration   = db.Column(db.Integer, nullable=False)    # saniye cinsinden
    start_time = db.Column(db.DateTime, nullable=False)   # sınav açılış zamanı
    end_time   = db.Column(db.DateTime, nullable=False)   # sınav kapanış zamanı

    teacher   = db.relationship('User', backref='exams', foreign_keys=[teacher_id])
    questions = db.relationship('Question', backref='exam', lazy=True)

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