from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Menggunakan kunci acak untuk keamanan sesi
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Membuat folder uploads jika belum ada
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Fungsi Setup untuk Fuzzy Logic
def setup_fuzzy():
    # Rentang 1-5 untuk input dan output
    metode_pengajaran = ctrl.Antecedent(np.arange(1, 6, 1), 'metode_pengajaran')
    fasilitas_pembelajaran = ctrl.Antecedent(np.arange(1, 6, 1), 'fasilitas_pembelajaran')
    tingkat_kepuasan = ctrl.Consequent(np.arange(1, 6, 1), 'tingkat_kepuasan')

    # Definisi membership function untuk input (metode_pengajaran, fasilitas_pembelajaran)
    metode_pengajaran['sangat_buruk'] = fuzz.trimf(metode_pengajaran.universe, [1, 1, 2])
    metode_pengajaran['buruk'] = fuzz.trimf(metode_pengajaran.universe, [1, 2, 3])
    metode_pengajaran['cukup_baik'] = fuzz.trimf(metode_pengajaran.universe, [2, 3, 4])
    metode_pengajaran['baik'] = fuzz.trimf(metode_pengajaran.universe, [3, 4, 5])
    metode_pengajaran['sangat_baik'] = fuzz.trimf(metode_pengajaran.universe, [4, 5, 5])

    fasilitas_pembelajaran['sangat_buruk'] = fuzz.trimf(fasilitas_pembelajaran.universe, [1, 1, 2])
    fasilitas_pembelajaran['buruk'] = fuzz.trimf(fasilitas_pembelajaran.universe, [1, 2, 3])
    fasilitas_pembelajaran['cukup_baik'] = fuzz.trimf(fasilitas_pembelajaran.universe, [2, 3, 4])
    fasilitas_pembelajaran['baik'] = fuzz.trimf(fasilitas_pembelajaran.universe, [3, 4, 5])
    fasilitas_pembelajaran['sangat_baik'] = fuzz.trimf(fasilitas_pembelajaran.universe, [4, 5, 5])

    # Definisi membership function untuk output (tingkat_kepuasan)
    tingkat_kepuasan['sangat_buruk'] = fuzz.trimf(tingkat_kepuasan.universe, [1, 1, 2])
    tingkat_kepuasan['buruk'] = fuzz.trimf(tingkat_kepuasan.universe, [1, 2, 3])
    tingkat_kepuasan['cukup_baik'] = fuzz.trimf(tingkat_kepuasan.universe, [2, 3, 4])
    tingkat_kepuasan['baik'] = fuzz.trimf(tingkat_kepuasan.universe, [3, 4, 5])
    tingkat_kepuasan['sangat_baik'] = fuzz.trimf(tingkat_kepuasan.universe, [4, 5, 5])

    # Definisikan aturan
    rule1 = ctrl.Rule(metode_pengajaran['sangat_baik'] & fasilitas_pembelajaran['sangat_baik'], tingkat_kepuasan['sangat_baik'])
    rule2 = ctrl.Rule(metode_pengajaran['baik'] & fasilitas_pembelajaran['baik'], tingkat_kepuasan['baik'])
    rule3 = ctrl.Rule(metode_pengajaran['cukup_baik'] & fasilitas_pembelajaran['cukup_baik'], tingkat_kepuasan['cukup_baik'])
    rule4 = ctrl.Rule(metode_pengajaran['buruk'] & fasilitas_pembelajaran['buruk'], tingkat_kepuasan['buruk'])
    rule5 = ctrl.Rule(metode_pengajaran['sangat_buruk'] & fasilitas_pembelajaran['sangat_buruk'], tingkat_kepuasan['sangat_buruk'])

    # Kontrol Sistem
    kepuasan_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5])
    return ctrl.ControlSystemSimulation(kepuasan_ctrl)

# Inisialisasi Sistem Fuzzy
kepuasan_simulasi = setup_fuzzy()

# Fungsi untuk menentukan predikat berdasarkan nilai kepuasan
def get_predikat_kepuasan(nilai):
    nilai = round(nilai)  # Pembulatan ke nilai terdekat
    if nilai == 5:
        return "Sangat Baik"
    elif nilai == 4:
        return "Baik"
    elif nilai == 3:
        return "Cukup Baik"
    elif nilai == 2:
        return "Buruk"
    else:
        return "Sangat Buruk"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # Baca data dari file Excel
        try:
            df = pd.read_excel(filepath, engine='openpyxl')  # Pastikan menggunakan openpyxl untuk format .xlsx
            print(df.head())  # Menampilkan 5 baris pertama dari data yang dibaca
        except Exception as e:
            return jsonify({'error': f'Error reading the Excel file: {e}'}), 400

        # Pastikan kolom ada dalam file Excel
        if not {'metode_pengajaran', 'fasilitas_pembelajaran'}.issubset(df.columns):
            return jsonify({'error': 'File harus memiliki kolom metode_pengajaran dan fasilitas_pembelajaran'}), 400

        total_kepuasan = 0
        jumlah_responden = len(df)

        # Proses setiap baris data dan hitung kepuasan per responden
        for _, row in df.iterrows():
            metode_pengajaran = int(row['metode_pengajaran'])
            fasilitas_pembelajaran = int(row['fasilitas_pembelajaran'])

            # Menjalankan fuzzy logic
            kepuasan_simulasi.input['metode_pengajaran'] = metode_pengajaran
            kepuasan_simulasi.input['fasilitas_pembelajaran'] = fasilitas_pembelajaran
            kepuasan_simulasi.compute()

            # Mengambil hasil kepuasan
            hasil_kepuasan = kepuasan_simulasi.output.get('tingkat_kepuasan', None)
            if hasil_kepuasan is not None:
                total_kepuasan += float(hasil_kepuasan)

        # Hitung rata-rata tingkat kepuasan
        rata_kepuasan = total_kepuasan / jumlah_responden if jumlah_responden > 0 else 0
        predikat_akhir = get_predikat_kepuasan(rata_kepuasan)

        # Menyimpan hasil di session agar bisa digunakan di halaman result.html
        session['rata_kepuasan'] = round(rata_kepuasan, 2)
        session['predikat_akhir'] = predikat_akhir

        return redirect(url_for('result'))  # Redirect ke halaman result

@app.route('/result')
def result():
    # Mengirimkan hasil evaluasi kepuasan ke halaman result.html
    if 'rata_kepuasan' not in session:
        return redirect(url_for('index'))  # Kembali ke halaman utama jika tidak ada hasil

    rata_kepuasan = session['rata_kepuasan']
    predikat_akhir = session['predikat_akhir']
    
    return render_template('result.html', rata_kepuasan=rata_kepuasan, predikat_akhir=predikat_akhir)

if __name__ == "__main__":
    app.run(debug=True)
