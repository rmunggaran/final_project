from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import os
import re

from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

app = Flask(__name__)
app.secret_key = 'aman' 

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# ===================== collection ====================
users_collection = db.users
profile_collection = db.profile
contact_collection = db.contact
layanan_collection = db.layanan
promo_collection = db.promo


# ============== Filter ================
def limit_taxt(value, word_limit):
    words = value.split()
    if len(words) > word_limit:
        return ' '.join(words[:word_limit]) + '...'
    return value

app.jinja_env.filters['limit_taxt'] = limit_taxt 

@app.template_filter('format_rupiah')
def format_rupiah(value):
    try:
        value = int(value)
        return f"{value:,.0f}".replace(",", ".")
    except ValueError:
        return value
    
@app.template_filter('format_date')
def format_date(value):
    try:
        date_obj = datetime.strptime(value, "%Y-%m-%d")
        return date_obj.strftime("%d %b %Y").lower().replace('may', 'mei')
    except ValueError:
        return value

# ============== end Filter ================

# ================ User ====================
@app.route('/')
def home():
    return render_template('home.html')
# ================ end User ====================

# ================ Login ====================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if 'username' in session:
        flash('Anda sudah login!', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users_collection.find_one({"username": username})

        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)
        flash('Anda telah logout.', 'info')
        return redirect(url_for('home'))
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))
# ================ End Login ====================


# ================ Dashboard Admin ====================
@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        today = datetime.now()
        return render_template(
            'dashboard.html', 
            title = "Dashboard",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y')
            )
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))
    
    
@app.route('/editprofile', methods=['POST'])
def edit_user():
    try:
        user_id = request.form.get('id')
        user = users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            return jsonify({'status': 'error', 'msg': f'Error: User tidak ditemukan.'})

        username = request.form.get('username')
        kelamin = request.form.get('kelamin')
        tgl_lahir = request.form.get('tgl_lahir')
        alamat = request.form.get('alamat')
        no_telepon = request.form.get('no_telepon')

        profile = request.files.get('foto_profil')
        
        update_data = {
            "username": username,
            "kelamin": kelamin,
            "tgl_lahir": tgl_lahir,
            "alamat": alamat,
            "tlp": no_telepon
        }

        if profile:
            extension = profile.filename.split('.')[-1]
            profilename = f'profile-{username}.{extension}'
            profile_save = f'static/img/profile/{profilename}'

            if os.path.exists(profile_save):
                os.remove(profile_save)

            profile.save(profile_save)

            update_data["foto_profil"] = profilename

        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

        if result.modified_count > 0:
            return jsonify({'status': 'success', 'msg': 'Data user berhasil diperbarui'})
        else:
            return jsonify({'status': 'warning', 'msg': 'Tidak ada perubahan data.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': f'Error: {e}'})

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))
    
    user_id = request.form.get('id')
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    new_password_confirmation = request.form.get('new_password_confirmation')

    if not check_password_hash(user['password'], current_password):
        return jsonify({'status': 'warning', 'msg': f'Password lama salah'})

    if new_password != new_password_confirmation:
        return jsonify({'status': 'warning', 'msg': f'Password baru dan konfirmasi password tidak cocok.'})

    if len(new_password) < 6:
        return jsonify({'status': 'warning', 'msg': f'Password baru harus lebih dari 6 karakter.'})

    hashed_password = generate_password_hash(new_password)
    result = users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed_password}}
    )
    if result.modified_count > 0:
        return jsonify({'status': 'success', 'msg': 'Password berhasil diganti.'})
    else:
        return jsonify({'status': 'error', 'msg': f'Error: Terjadi kesalahan, password tidak dapat diubah.'})
# ================ End Dashboard Admin ====================    


# ================ Profile perusahaan ====================
@app.route('/profilePerusahaan', methods=['GET', 'POST'])
def profilePerusahaan():
    if 'username' in session:
        if request.method == 'POST':
            try:
                namaPerusahaan = request.form.get('namaPerusahaan')
                deskripsi = request.form.get('deskripsi')
                visi = request.form.get('visi')
                misi = request.form.get('misi')
                logo = request.files.get('logo')

                insert_data = {
                    "namaPerusahaan": namaPerusahaan,
                    "deskripsi": deskripsi,
                    "visi": visi,
                    "misi": misi
                }

                if logo:
                    extension = logo.filename.split('.')[-1]
                    logoname = f'logo-{logo.filename}.{extension}'
                    logo_save = f'static/img/logo/{logoname}'

                    if os.path.exists(logo_save):
                        os.remove(logo_save)

                    logo.save(logo_save)

                    insert_data["logo"] = logoname

                result = profile_collection.insert_one(insert_data)

                if result.inserted_id:
                    return jsonify({'status': 'success', 'msg': 'Profile Perusahaan berhasil ditambahkan'})
                else:
                    return jsonify({'status': 'warning', 'msg': 'Tidak ada penambahan data.'})

            except Exception as e:
                return jsonify({'status': 'error', 'msg': f'Error: {e}'})

        today = datetime.now()
        return render_template(
            'profilePerusahaan.html', 
            title = "Profile Perusahaan",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y'),
            data = profile_collection.find_one(),
            )
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))


@app.route('/profilePerusahaanEdit', methods=['POST'])
def profilePerusahaanEdit():
    if 'username' in session:
        try:
            profile_id = request.form.get('id')
            profile = profile_collection.find_one({"_id": ObjectId(profile_id)})

            if not profile:
                return jsonify({'status': 'error', 'msg': f'Error: Profile Perusahaan tidak ditemukan.'})

            namaPerusahaan = request.form.get('namaPerusahaan')
            deskripsi = request.form.get('deskripsi')
            visi = request.form.get('visi')
            misi = request.form.get('misi')
            logo = request.files.get('logo')

            update_data = {
                "namaPerusahaan": namaPerusahaan,
                "deskripsi": deskripsi,
                "visi": visi,
                "misi": misi
            }

            if logo:
                extension = logo.filename.split('.')[-1]
                logoname = f'logo-{logo.filename}.{extension}'
                logo_save = f'static/img/logo/{logoname}'
                if os.path.exists(logo_save):
                    os.remove(logo_save)
                logo.save(logo_save)
                update_data["logo"] = logoname

            result = profile_collection.update_one(
                {"_id": ObjectId(profile_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return jsonify({'status': 'success', 'msg': 'Data Profile perusahaan berhasil diperbarui'})
            else:
                return jsonify({'status': 'warning', 'msg': 'Tidak ada perubahan data.'})
        except Exception as e:
            return jsonify({'status': 'error', 'msg': f'Error: {e}'})
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))
# ================ End Profile perusahaan ====================


# ================ Data Contact ====================
@app.route('/dataContact', methods=['GET', 'POST'])
def dataContact():
    if 'username' in session:
        if request.method == 'POST':
            try:
                nomor = request.form.get('nomor')
                email = request.form.get('email')
                alamat = request.form.get('alamat')
                hari_buka_dari = request.form.get('hariBukaDari')
                hari_buka_sampai = request.form.get('hariBukaSampai')
                jam_buka_dari = request.form.get('jamBukaDari')
                jam_buka_sampai = request.form.get('jamBukaSampai')
                tt = request.form.get('tt')
                ig = request.form.get('ig')
                maps = request.form.get('maps')

                maps_updated = maps.replace('width="600"', 'width="100%"').replace('height="450"', 'height="100%"')

                contact_data = {
                    "nomor": nomor,
                    "email": email,
                    "alamat": alamat,
                    "hari_buka": {
                        "dari": hari_buka_dari,
                        "sampai": hari_buka_sampai
                    },
                    "jam_buka": {
                        "dari": jam_buka_dari,
                        "sampai": jam_buka_sampai
                    },
                    "social_media": {
                        "tiktok": tt,
                        "instagram": ig
                    },
                    "maps": maps_updated
                }

                result = contact_collection.insert_one(contact_data)

                if result.inserted_id:
                    return jsonify({'status': 'success', 'msg': 'Contact berhasil ditambahkan'})
                else:
                    return jsonify({'status': 'warning', 'msg': 'Tidak ada penambahan data.'})

            except Exception as e:
                return jsonify({'status': 'error', 'msg': f'Error: {e}'})

        today = datetime.now()
        return render_template(
            'dataContact.html', 
            title = "Data Contact",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y'),
            data = contact_collection.find_one(),
            )
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))


@app.route('/dataContactEdit', methods=['POST'])
def dataContactEdit():
    if 'username' in session:
        try:
            contact_id = request.form.get('id')
            contact = contact_collection.find_one({"_id": ObjectId(contact_id)})

            if not contact:
                return jsonify({'status': 'error', 'msg': f'Error: Contact Perusahaan tidak ditemukan.'})

            nomor = request.form.get('nomor')
            email = request.form.get('email')
            alamat = request.form.get('alamat')
            hari_buka_dari = request.form.get('hariBukaDari')
            hari_buka_sampai = request.form.get('hariBukaSampai')
            jam_buka_dari = request.form.get('jamBukaDari')
            jam_buka_sampai = request.form.get('jamBukaSampai')
            tt = request.form.get('tt')
            ig = request.form.get('ig')
            maps = request.form.get('maps')

            maps_updated = maps.replace('width="600"', 'width="100%"').replace('height="450"', 'height="100%"')

            contact_data = {
                "nomor": nomor,
                "email": email,
                "alamat": alamat,
                "hari_buka": {
                    "dari": hari_buka_dari,
                    "sampai": hari_buka_sampai
                },
                "jam_buka": {
                    "dari": jam_buka_dari,
                    "sampai": jam_buka_sampai
                },
                "social_media": {
                    "tiktok": tt,
                    "instagram": ig
                },
                "maps": maps_updated
            }

            result = contact_collection.update_one(
                {"_id": ObjectId(contact_id)},
                {"$set": contact_data}
            )

            if result.modified_count > 0:
                return jsonify({'status': 'success', 'msg': 'Data Profile perusahaan berhasil diperbarui'})
            else:
                return jsonify({'status': 'warning', 'msg': 'Tidak ada perubahan data.'})
        except Exception as e:
            return jsonify({'status': 'error', 'msg': f'Error: {e}'})
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))
# ================ End Data Contact ====================


# ========================= Data Layanan ========================
@app.route('/dataLayanan', methods=['GET', 'POST'])
def dataLayanan():
    if 'username' in session:
        if request.method == 'POST':
            try:
                judul = request.form.get('judul')
                harga = request.form.get('harga')
                deskripsi = request.form.get('deskripsi')
                foto = request.files.get('foto')

                insert_data = {
                    "judul": judul,
                    "harga": harga,
                    "deskripsi": deskripsi
                }

                if foto:
                    extension = foto.filename.split('.')[-1]
                    fotoname = f'foto-{judul}.{extension}'
                    foto_save = f'static/img/layanan/{fotoname}'

                    if os.path.exists(foto_save):
                        os.remove(foto_save)

                    foto.save(foto_save)

                    insert_data["foto"] = fotoname

                result = layanan_collection.insert_one(insert_data)

                if result.inserted_id:
                    return jsonify({'status': 'success', 'msg': 'Layanan berhasil ditambahkan'})
                else:
                    return jsonify({'status': 'warning', 'msg': 'Tidak ada penambahan data.'})

            except Exception as e:
                return jsonify({'status': 'error', 'msg': f'Error: {e}'})

        today = datetime.now()
        return render_template(
            'dataLayanan.html', 
            title = "Data Layanan",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y'),
            data = layanan_collection.find(),
            data_count = layanan_collection.count_documents({})
            )
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))


@app.route('/dataLayananEdit', methods=['POST'])
def dataLayananEdit():
    if 'username' in session:
        try:
            layanan_id = request.form.get('id')
            layanan = layanan_collection.find_one({"_id": ObjectId(layanan_id)})

            if not layanan:
                return jsonify({'status': 'error', 'msg': f'Error: Id layanan tidak ditemukan.'})

            judul = request.form.get('judul')
            harga = request.form.get('harga')
            deskripsi = request.form.get('deskripsi')
            foto = request.files.get('foto')

            update_data = {
                "judul": judul,
                "harga": harga,
                "deskripsi": deskripsi
            }

            if foto:
                extension = foto.filename.split('.')[-1]
                fotoname = f'foto-{judul}.{extension}'
                foto_save = f'static/img/layanan/{fotoname}'
                foto_old = f'static/img/layanan/{fotoname}'
                if os.path.exists(foto_old):
                    os.remove(foto_save)
                foto.save(foto_save)
                update_data["foto"] = fotoname

            result = layanan_collection.update_one(
                {"_id": ObjectId(layanan_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return jsonify({'status': 'success', 'msg': 'Layanan berhasil ditambahkan'})
            else:
                return jsonify({'status': 'warning', 'msg': 'Tidak ada penambahan data.'})

        except Exception as e:
            return jsonify({'status': 'error', 'msg': f'Error: {e}'})

    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))


@app.route('/hapus_layanan', methods=['POST'])
def hapus_layanan():
    try:
        id = request.form.get('id')
        layanan = layanan_collection.find_one({'_id': ObjectId(id)})
        
        if not layanan:
            return jsonify({'status': 'warning', 'msg': 'Data tidak ditemukan.'})
        
        foto = layanan.get('foto')
        if foto:
            foto_path = os.path.join('static', 'img', 'layanan', foto)
            if os.path.exists(foto_path):
                os.remove(foto_path) 

        result = layanan_collection.delete_one({'_id': ObjectId(id)})

        if result.deleted_count > 0:
            return jsonify({'status': 'success', 'msg': 'Layanan berhasil dihapus beserta file foto.'})
        else:
            return jsonify({'status': 'warning', 'msg': 'Gagal menghapus data.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': f'Error: {str(e)}'})

@app.route('/dataLayanan/searchLayanan', methods=['GET'])
def search_layanan():
    query = request.args.get('query', '') 
    if query:  
        results = layanan_collection.find({
            "judul": {"$regex": query, "$options": "i"}
        })
        results = list(results)  
    else:
        results = layanan_collection.find()

    today = datetime.now()
    return render_template(
        'dataLayanan.html', 
            title = "Data Layanan",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y'),
            data=results, 
            data_count = layanan_collection.count_documents({}), 
            query=query)
# ========================= End Data Layanan ========================

# ========================= Data Promo ========================
@app.route('/dataPromo', methods=['GET', 'POST'])
def dataPromo():
    if 'username' in session:
        if request.method == 'POST':
            try:
                judul = request.form.get('judul')
                tb = request.form.get('tb')
                deskripsi = request.form.get('deskripsi')
                foto = request.files.get('foto')

                insert_data = {
                    "judul": judul,
                    "tanggal_berakhir": tb,
                    "deskripsi": deskripsi
                }

                if foto:
                    extension = foto.filename.split('.')[-1]
                    fotoname = f'foto-{judul}.{extension}'
                    foto_save = f'static/img/promo/{fotoname}'

                    if os.path.exists(foto_save):
                        os.remove(foto_save)

                    foto.save(foto_save)

                    insert_data["foto"] = fotoname

                result = promo_collection.insert_one(insert_data)

                if result.inserted_id:
                    return jsonify({'status': 'success', 'msg': 'Promo berhasil ditambahkan'})
                else:
                    return jsonify({'status': 'warning', 'msg': 'Tidak ada penambahan data.'})

            except Exception as e:
                return jsonify({'status': 'error', 'msg': f'Error: {e}'})

        today = datetime.now()
        return render_template(
            'dataPromo.html', 
            title = "Data Promo",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y'),
            data = promo_collection.find(),
            data_count = promo_collection.count_documents({})
            )
    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

@app.route('/dataPromoEdit', methods=['POST'])
def dataPromoEdit():
    if 'username' in session:
        try:
            promo_id = request.form.get('id')
            promo = promo_collection.find_one({"_id": ObjectId(promo_id)})

            if not promo:
                return jsonify({'status': 'error', 'msg': f'Error: Id promo tidak ditemukan.'})

            judul = request.form.get('judul')
            tb = request.form.get('tb')
            deskripsi = request.form.get('deskripsi')
            foto = request.files.get('foto')

            update_data = {
                "judul": judul,
                "tanggal_berakhir": tb,
                "deskripsi": deskripsi
            }

            if foto:
                extension = foto.filename.split('.')[-1]
                fotoname = f'foto-{judul}.{extension}'
                foto_save = f'static/img/promo/{fotoname}'
                if os.path.exists(foto_save):
                    os.remove(foto_save)
                foto.save(foto_save)
                update_data["foto"] = fotoname

            result = promo_collection.update_one(
                {"_id": ObjectId(promo_id)},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return jsonify({'status': 'success', 'msg': 'Promo berhasil ditambahkan'})
            else:
                return jsonify({'status': 'warning', 'msg': 'Tidak ada penambahan data.'})

        except Exception as e:
            return jsonify({'status': 'error', 'msg': f'Error: {e}'})

    else:
        flash('Harap login terlebih dahulu!', 'warning')
        return redirect(url_for('login'))

@app.route('/hapus_promo', methods=['POST'])
def hapus_promo():
    try:
        id = request.form.get('id')
        promo = promo_collection.find_one({'_id': ObjectId(id)})
        
        if not promo:
            return jsonify({'status': 'warning', 'msg': 'Data tidak ditemukan.'})
        
        foto = promo.get('foto')
        if foto:
            foto_path = os.path.join('static', 'img', 'promo', foto)
            if os.path.exists(foto_path):
                os.remove(foto_path) 

        result = promo_collection.delete_one({'_id': ObjectId(id)})

        if result.deleted_count > 0:
            return jsonify({'status': 'success', 'msg': 'Promo berhasil dihapus beserta file foto.'})
        else:
            return jsonify({'status': 'warning', 'msg': 'Gagal menghapus data.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': f'Error: {str(e)}'})

@app.route('/dataPromo/searchPromo', methods=['GET'])
def search_promo():
    query = request.args.get('query', '') 
    if query:  
        results = promo_collection.find({
            "judul": {"$regex": query, "$options": "i"}
        })
        results = list(results)  
    else:
        results = promo_collection.find()

    today = datetime.now()
    return render_template(
        'dataPromo.html', 
            title = "Data Promo",
            user = users_collection.find_one({"username": session['username']}),
            time = today.strftime('%d %B %Y'),
            data=results, 
            data_count = promo_collection.count_documents({}), 
            query=query)
# ========================= End Data Promo ========================

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)