import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Exam, Question, Result
from models import UserAnswer

app = Flask(__name__)

# --- YAPILANDIRMA ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' 
app.config['SECRET_KEY'] = 'muhendislik_projesi_cok_gizli_anahtar' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- VERİTABANI BAŞLANGIÇ VERİLERİ ---
def seed_data():
    if not User.query.filter_by(email='ogrenci@test.com').first():
        hoca = User(email='hoca@test.com', password='123', role='teacher')
        ogrenci = User(email='ogrenci@test.com', password='123', role='student')
        db.session.add(hoca)
        db.session.add(ogrenci)
        db.session.commit()
        print("Sistem: Test kullanıcıları yüklendi!")

# --- ROTALAR ---

# 1. Giriş Sayfası
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, password=password).first()
        
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('exams_list'))
        else:
            flash('Hatalı giriş bilgileri!', 'danger')
            
    return render_template('login.html')

# 2. Kayıt Olma Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(email=email).first():
            flash('Bu e-posta zaten kayıtlı!', 'warning')
        else:
            new_user = User(email=email, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
            return redirect(url_for('index'))
            
    return render_template('register.html')
    
# 3. Öğretmen Paneli
@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    current_user = User.query.get(session['user_id']) 
    exams = Exam.query.all()
    results = Result.query.all()
    
    total_exams = len(exams)
    total_participation = len(results)
    avg_score = sum([r.score for r in results]) / total_participation if total_participation > 0 else 0
    
    return render_template('teacher_dashboard.html', 
                           current_user=current_user,
                           exams=exams, 
                           results=results, 
                           total_exams=total_exams, 
                           total_participation=total_participation, 
                           avg_score=round(avg_score))

# 4. Sınav Oluşturma
@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        duration = int(request.form.get('duration')) * 60
        question_count = int(request.form.get('question_count'))
        
        new_exam = Exam(title=title, duration=duration)
        db.session.add(new_exam)
        db.session.commit()
        
        for i in range(1, question_count + 1):
            q_text = request.form.get(f'q_text_{i}')
            opt_a = request.form.get(f'q_opt_a_{i}')
            opt_b = request.form.get(f'q_opt_b_{i}')
            opt_c = request.form.get(f'q_opt_c_{i}')
            opt_d = request.form.get(f'q_opt_d_{i}')
            correct_choice = request.form.get(f'q_correct_{i}')
            
            options_str = f"{opt_a}, {opt_b}, {opt_c}, {opt_d}"
            
            correct_answer_text = ""
            if correct_choice == 'A': correct_answer_text = opt_a
            elif correct_choice == 'B': correct_answer_text = opt_b
            elif correct_choice == 'C': correct_answer_text = opt_c
            elif correct_choice == 'D': correct_answer_text = opt_d
            
            new_q = Question(exam_id=new_exam.id, text=q_text, options_json=options_str, correct_answer=correct_answer_text)
            db.session.add(new_q)
            
        db.session.commit()
        flash(f'Sınav ve {question_count} adet soru başarıyla oluşturuldu!', 'success')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('create_exam.html')

# 5. Öğrenci Sınav Listesi
@app.route('/exams')
def exams_list():
    if not session.get('user_id'):
        return redirect(url_for('index'))
        
    current_user = User.query.get(session['user_id'])
    all_exams = Exam.query.all()
    
    # Öğrencinin girdiği tüm sınavların sonuçlarını alıyoruz
    user_results = Result.query.filter_by(user_id=current_user.id).all()
    # Şablonda kolay bulmak için sözlük (dictionary) yapısına çeviriyoruz
    completed_exams = {res.exam_id: res for res in user_results}
    
    return render_template('exams.html', exams=all_exams, current_user=current_user, completed_exams=completed_exams)

# 6. Sınav Uygulama Ekranı
@app.route('/exam/<int:exam_id>', methods=['GET', 'POST'])
def take_exam(exam_id):
    if not session.get('user_id'):
        return redirect(url_for('index'))
        
    current_user = User.query.get(session['user_id'])
    
    existing_result = Result.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    if existing_result:
        return redirect(url_for('exams_list'))
        
    current_exam = Exam.query.get_or_404(exam_id)
    
    if request.method == 'POST':
        correct_count = 0
        questions = current_exam.questions
        analysis_data = []
        
        # 1. Önce Puanı Hesapla ve Result'ı Oluştur
        for q in questions:
            ans = request.form.get(f'question_{q.id}')
            if ans == q.correct_answer:
                correct_count += 1
                
        total_questions = len(questions)
        score = (correct_count / total_questions) * 100 if total_questions else 0
        
        new_result = Result(user_id=session['user_id'], exam_id=exam_id, score=score)
        db.session.add(new_result)
        db.session.flush() # Result'ın ID'sini alabilmek için geçici olarak kaydediyoruz
        
        # 2. Şimdi Her Bir Cevabı Veritabanına (UserAnswer) Kaydet
        for index, q in enumerate(questions):
            ans = request.form.get(f'question_{q.id}')
            is_correct = (ans == q.correct_answer)
            user_ans_text = ans if ans else "Boş Bırakıldı"
            
            # Veritabanına kaydedilen cevap
            new_answer = UserAnswer(
                result_id=new_result.id, 
                question_id=q.id, 
                selected_answer=user_ans_text, 
                is_correct=is_correct
            )
            db.session.add(new_answer)
            
            # Öğrenci sonuç ekranı için oluşturulan liste
            analysis_data.append({
                'number': index + 1,
                'text': q.text,
                'user_answer': user_ans_text,
                'correct_answer': q.correct_answer,
                'is_correct': is_correct
            })
            
        db.session.commit() # Tüm işlemleri kalıcı olarak veritabanına yaz
        
        user_initials = current_user.email[:2].upper()
        
        return render_template('result.html', 
                               score=score,
                               correct_count=correct_count,
                               wrong_count=total_questions - correct_count,
                               total_questions=total_questions,
                               exam_title=current_exam.title,
                               analysis_data=analysis_data,
                               user_initials=user_initials)
                               
    return render_template('exam.html', exam=current_exam)

# 7. Öğrenci Sınav Detayı (Öğretmen İçin) - YUKARI TAŞINDI!
@app.route('/student_details/<int:result_id>')
def student_details(result_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    result = Result.query.get_or_404(result_id)
    return render_template('student_details.html', result=result)

# 8. Çıkış Yap
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)