from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Exam, Question, Result, UserAnswer

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'muhendislik_projesi_cok_gizli_anahtar'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

LEVEL_LABELS = {
    'ilkokul':    'İlkokul',
    'ortaokul':   'Ortaokul',
    'lise':       'Lise',
    'universite': 'Üniversite',
}


# ─── YARDIMCI ─────────────────────────────────────────────────────────────────
def login_required(role=None):
    if not session.get('user_id'):
        return redirect(url_for('index'))
    if role and session.get('role') != role:
        return redirect(url_for('index'))
    return None


# ─── 1. GİRİŞ ────────────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        user     = User.query.filter_by(email=email, password=password).first()

        if user:
            session['user_id'] = user.id
            session['role']    = user.role
            session['name']    = user.name

            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))

            # Öğrenci profili eksikse önce profile yönlendir
            if not user.profile_complete:
                flash('Sınavlara erişmek için lütfen önce profilinizi tamamlayın.', 'warning')
                return redirect(url_for('student_profile'))

            return redirect(url_for('exams_list'))
        else:
            flash('Hatalı e-posta veya şifre!', 'danger')

    return render_template('login.html')


# ─── 2. KAYIT ────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form.get('name')
        email    = request.form.get('email')
        password = request.form.get('password')
        role     = request.form.get('role')

        if User.query.filter_by(email=email).first():
            flash('Bu e-posta zaten kayıtlı!', 'warning')
        else:
            db.session.add(User(name=name, email=email, password=password, role=role))
            db.session.commit()
            flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
            return redirect(url_for('index'))

    return render_template('register.html')


# ─── 3. ÖĞRENCİ PROFİL ───────────────────────────────────────────────────────
@app.route('/profile', methods=['GET', 'POST'])
def student_profile():
    redir = login_required(role='student')
    if redir: return redir

    student = User.query.get(session['user_id'])

    if request.method == 'POST':
        level = request.form.get('school_level')
        grade = request.form.get('grade')

        if level not in ['ilkokul', 'ortaokul', 'lise', 'universite']:
            flash('Geçerli bir okul düzeyi seçiniz!', 'danger')
            return redirect(url_for('student_profile'))

        if not grade or int(grade) not in [1, 2, 3, 4]:
            flash('Geçerli bir sınıf seçiniz!', 'danger')
            return redirect(url_for('student_profile'))

        student.school_level = level
        student.grade        = int(grade)
        db.session.commit()
        flash('Profiliniz güncellendi!', 'success')
        return redirect(url_for('exams_list'))

    return render_template('student_profile.html', student=student, level_labels=LEVEL_LABELS)


# ─── 4. ÖĞRETMEN PANELİ ──────────────────────────────────────────────────────
@app.route('/teacher')
def teacher_dashboard():
    redir = login_required(role='teacher')
    if redir: return redir

    teacher  = User.query.get(session['user_id'])
    exams    = Exam.query.filter_by(teacher_id=teacher.id).all()
    exam_ids = [e.id for e in exams]
    results  = Result.query.filter(Result.exam_id.in_(exam_ids)).all() if exam_ids else []

    total_exams         = len(exams)
    total_participation = len(results)
    avg_score = round(sum(r.score for r in results) / total_participation) if total_participation else 0

    return render_template('teacher_dashboard.html',
                           current_user=teacher,
                           exams=exams,
                           results=results,
                           total_exams=total_exams,
                           total_participation=total_participation,
                           avg_score=avg_score,
                           level_labels=LEVEL_LABELS)


# ─── 5. SINAV OLUŞTUR ────────────────────────────────────────────────────────
@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    redir = login_required(role='teacher')
    if redir: return redir

    teacher = User.query.get(session['user_id'])

    if request.method == 'POST':
        title          = request.form.get('title')
        duration       = int(request.form.get('duration')) * 60
        question_count = int(request.form.get('question_count'))
        start_str      = request.form.get('start_time')
        end_str        = request.form.get('end_time')
        target_level   = request.form.get('target_level')
        target_grade   = request.form.get('target_grade')

        try:
            start_time = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
            end_time   = datetime.strptime(end_str,   '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Geçersiz tarih/saat formatı!', 'danger')
            return redirect(url_for('create_exam'))

        if end_time <= start_time:
            flash('Bitiş zamanı başlangıçtan sonra olmalıdır!', 'danger')
            return redirect(url_for('create_exam'))

        if target_level not in ['ilkokul', 'ortaokul', 'lise', 'universite']:
            flash('Geçerli bir okul düzeyi seçiniz!', 'danger')
            return redirect(url_for('create_exam'))

        new_exam = Exam(
            teacher_id   = teacher.id,
            title        = title,
            duration     = duration,
            start_time   = start_time,
            end_time     = end_time,
            target_level = target_level,
            target_grade = int(target_grade)
        )
        db.session.add(new_exam)
        db.session.commit()

        for i in range(1, question_count + 1):
            opt_a  = request.form.get(f'q_opt_a_{i}')
            opt_b  = request.form.get(f'q_opt_b_{i}')
            opt_c  = request.form.get(f'q_opt_c_{i}')
            opt_d  = request.form.get(f'q_opt_d_{i}')
            choice = request.form.get(f'q_correct_{i}')
            correct = {'A': opt_a, 'B': opt_b, 'C': opt_c, 'D': opt_d}.get(choice, '')
            db.session.add(Question(
                exam_id        = new_exam.id,
                text           = request.form.get(f'q_text_{i}'),
                options_json   = f"{opt_a}, {opt_b}, {opt_c}, {opt_d}",
                correct_answer = correct
            ))

        db.session.commit()
        flash(f'"{title}" sınavı oluşturuldu!', 'success')
        return redirect(url_for('teacher_dashboard'))

    return render_template('create_exam.html')


# ─── 6. ÖĞRENCİ SINAV LİSTESİ ────────────────────────────────────────────────
@app.route('/exams')
def exams_list():
    redir = login_required()
    if redir: return redir

    student = User.query.get(session['user_id'])

    # Profil tamamlanmamışsa yönlendir
    if not student.profile_complete:
        flash('Sınavlara erişmek için lütfen önce profilinizi tamamlayın.', 'warning')
        return redirect(url_for('student_profile'))

    # Sadece öğrencinin düzey ve sınıfına uyan sınavlar
    exams = Exam.query.filter_by(
        target_level=student.school_level,
        target_grade=student.grade
    ).all()

    completed = {r.exam_id: r for r in Result.query.filter_by(user_id=student.id).all()}

    return render_template('exams.html',
                           exams=exams,
                           current_user=student,
                           completed_exams=completed,
                           level_labels=LEVEL_LABELS)


# ─── 7. SINAV EKRANI ─────────────────────────────────────────────────────────
@app.route('/exam/<int:exam_id>', methods=['GET', 'POST'])
def take_exam(exam_id):
    redir = login_required()
    if redir: return redir

    student = User.query.get(session['user_id'])
    exam    = Exam.query.get_or_404(exam_id)

    # Düzey/sınıf eşleşme kontrolü
    if exam.target_level != student.school_level or exam.target_grade != student.grade:
        flash('Bu sınava erişim yetkiniz yok!', 'danger')
        return redirect(url_for('exams_list'))

    # Daha önce girmiş mi?
    if Result.query.filter_by(user_id=student.id, exam_id=exam_id).first():
        flash('Bu sınavı zaten tamamladınız.', 'warning')
        return redirect(url_for('exams_list'))

    # Zaman penceresi kontrolü
    if not exam.is_active:
        flash('Bu sınav şu an aktif değil.', 'warning')
        return redirect(url_for('exams_list'))

    if request.method == 'POST':
        questions     = exam.questions
        correct_count = 0
        analysis_data = []

        for q in questions:
            ans        = request.form.get(f'question_{q.id}')
            is_correct = (ans == q.correct_answer)
            if is_correct:
                correct_count += 1

        total = len(questions)
        score = (correct_count / total) * 100 if total else 0

        result = Result(user_id=student.id, exam_id=exam_id, score=score)
        db.session.add(result)
        db.session.flush()

        for idx, q in enumerate(questions):
            ans        = request.form.get(f'question_{q.id}')
            is_correct = (ans == q.correct_answer)
            db.session.add(UserAnswer(
                result_id       = result.id,
                question_id     = q.id,
                selected_answer = ans if ans else 'Boş Bırakıldı',
                is_correct      = is_correct
            ))
            analysis_data.append({
                'number':         idx + 1,
                'text':           q.text,
                'user_answer':    ans if ans else 'Boş Bırakıldı',
                'correct_answer': q.correct_answer,
                'is_correct':     is_correct
            })

        db.session.commit()

        return render_template('result.html',
                               score=score,
                               correct_count=correct_count,
                               wrong_count=total - correct_count,
                               total_questions=total,
                               exam_title=exam.title,
                               analysis_data=analysis_data,
                               user_initials=student.name[:2].upper())

    return render_template('exam.html', exam=exam)


# ─── 8. ÖĞRENCİ DETAYI (öğretmen) ───────────────────────────────────────────
@app.route('/student_details/<int:result_id>')
def student_details(result_id):
    redir = login_required(role='teacher')
    if redir: return redir

    result  = Result.query.get_or_404(result_id)
    teacher = User.query.get(session['user_id'])

    if result.exam.teacher_id != teacher.id:
        flash('Bu sonuca erişim yetkiniz yok!', 'danger')
        return redirect(url_for('teacher_dashboard'))

    return render_template('student_details.html', result=result)


# ─── 9. ÇIKIŞ ────────────────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)