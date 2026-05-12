import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Exam, Question, Result

app = Flask(__name__)

# --- YAPILANDIRMA ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' 
app.config['SECRET_KEY'] = 'muhendislik_projesi_cok_gizli_anahtar' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- VERİTABANI BAŞLANGIÇ VERİLERİ ---
def seed_data():
    if not User.query.filter_by(email='ogrenci@test.com').first():
        # Örnek kullanıcılar
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
            # Role göre yönlendirme
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
        role = request.form.get('role') # 'student' veya 'teacher'
        
        if User.query.filter_by(email=email).first():
            flash('Bu e-posta zaten kayıtlı!', 'warning')
        else:
            new_user = User(email=email, password=password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
            return redirect(url_for('index'))
            
    return render_template('register.html')

# 3. Öğretmen Kontrol Paneli
@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    
    exams = Exam.query.all()
    results = Result.query.all() # Tüm sonuçları öğretmen görebilir
    return render_template('teacher_dashboard.html', exams=exams, results=results)

# 4. Sınav Oluşturma (Öğretmen İçin)
@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        duration = int(request.form.get('duration')) * 60 # Dakikayı saniyeye çevir
        
        new_exam = Exam(title=title, duration=duration)
        db.session.add(new_exam)
        db.session.commit()
        
        # Basitçe bir soru ekleme örneği
        q_text = request.form.get('question_text')
        q_options = request.form.get('options') # Virgülle ayrılmış: A, B, C, D
        q_correct = request.form.get('correct_answer')
        
        new_q = Question(
            exam_id=new_exam.id,
            text=q_text,
            options_json=q_options, # Frontend'den gelen string
            correct_answer=q_correct
        )
        db.session.add(new_q)
        db.session.commit()
        
        flash('Sınav ve soru başarıyla oluşturuldu!', 'success')
        return redirect(url_for('teacher_dashboard'))
        
    return render_template('create_exam.html')

# 5. Öğrenci Sınav Listesi
@app.route('/exams')
def exams_list():
    if not session.get('user_id'):
        return redirect(url_for('index'))
    all_exams = Exam.query.all()
    return render_template('exams.html', exams=all_exams)

# 6. Sınav Uygulama Ekranı
@app.route('/exam/<int:exam_id>', methods=['GET', 'POST'])
def take_exam(exam_id):
    if not session.get('user_id'):
        return redirect(url_for('index'))
        
    current_exam = Exam.query.get_or_404(exam_id)
    
    if request.method == 'POST':
        correct_count = 0
        questions = current_exam.questions
        for q in questions:
            ans = request.form.get(f'question_{q.id}')
            if ans == q.correct_answer:
                correct_count += 1
        
        # app.py içindeki take_exam fonksiyonunun son kısmı
        score = (correct_count / len(questions)) * 100 if questions else 0
        new_result = Result(user_id=session['user_id'], exam_id=exam_id, score=score)
        db.session.add(new_result)
        db.session.commit()
        
        # Burayı güncelledik: Artık result.html'e puanı gönderiyoruz
        return render_template('result.html', score=score)
        
    return render_template('exam.html', exam=current_exam)

# 7. Çıkış Yap
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)