# Violet Robot

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)
[![ForTheBadge built-with-love](http://ForTheBadge.com/images/badges/built-with-love.svg)](https://github.com/NoobPeoples/)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/8bfae649db3742a883e0ac1008755db3)](https://www.codacy.com/gh/NoobPeoples/Violet/dashboard?utm_source=github.com&utm_medium=referral&utm_content=NoobPeoples/Violet&utm_campaign=Badge_Grade)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/NoobPeoples/Violet/pulls)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/NoobPeoples/Violet/graphs/commit-activity)
![Logo](https://telegra.ph/file/b99bb9e7f762355c3aaf1.jpg)

Bot Python telegram modular yang berjalan di python3 dengan database sqlalchemy.

Awalnya bot manajemen grup sederhana dengan beberapa fitur admin, itu telah berkembang, menjadi sangat modular dan
mudah digunakan. Perhatikan bahwa proyek ini menggunakan bot Telegram terkenal pada masanya @BanhammerMarie_bot dari Paul Larson sebagai basisnya.

Dapat ditemukan di telegram sebagai [Violet](https://t.me/VioletsRobot).

Bergabunglah dengan [Dukungan Grup](https://t.me/Violet_support) jika Anda hanya ingin mengikuti info terbaru tentang fitur atau pengumuman baru.

## Deploy to Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/NoobPeoples/Violet)

## Credits

Skyleebot For Awesome Bot, And This Base in They

Skittbot for Stickers module and memes module.

1maverick1 for many stuff.

AyraHikari for weather modules and some other stuff.

RealAkito for reverse search modules.

MrYacha for connections module

ATechnoHazard for many stuffs

Corsicanu and Nunopenim for android modules

Any other missing Credits can be seen in commits!

## Starting the bot

Setelah Anda mengatur database Anda dan konfigurasi Anda (lihat di bawah) selesai, jalankan saja:

`python3 -m kaga`

## Menyiapkan bot Baca ini sebelum mencoba menggunakan

Harap pastikan untuk menggunakan python3.6 di atas, karena saya tidak dapat menjamin semuanya akan berfungsi seperti yang diharapkan pada versi Python yang lebih lama!
Ini karena penguraian penurunan harga dilakukan dengan iterasi melalui dict, yang diurutkan secara default di 3.6.

### Konfigurasi

Ada dua cara yang mungkin untuk mengonfigurasi bot Anda: file config.py, atau variabel ENV.

Versi yang disukai adalah menggunakan file `config.py`, karena ini lebih memudahkan untuk melihat semua pengaturan Anda secara bersamaan.
File ini harus ditempatkan di folder `UserindoBot` Anda, di samping file` __main__. Py`.
Di sinilah token bot Anda akan dimuat, serta URI database Anda (jika Anda menggunakan database), dan sebagian besar
pengaturan Anda yang lain.

Direkomendasikan untuk mengimpor sample_config dan memperluas kelas Config, karena ini akan memastikan konfigurasi Anda berisi semuanya
default diatur di sample_config, sehingga membuatnya lebih mudah untuk ditingkatkan.

Contoh file `config.env` bisa jadi:

```python
    API_KEY = "" # your bot Token from BotFather
    OWNER_ID = "1234567"  # If you dont know, run the bot and do /id in your private chat with it
    OWNER_USERNAME = "userbotindo" # your telegram username
    SQLALCHEMY_DATABASE_URI = "sqldbtype://username:pw@hostname:port/db_name"
    MONGO_DB_URI = "mongodb+srv://username:pwd@host.port.mongodb.net/db_name"
    MESSAGE_DUMP = "-100987654"  # needed to make sure 'save from' messages persist
    LOAD = "" # list of loaded modules (seperate with space)
    NO_LOAD = "afk android" # list of unloaded modules (seperate with space)
    STRICT_GBAN = True
```

### Python dependencies

Instal dependensi Python yang diperlukan dengan berpindah ke direktori proyek dan menjalankan:

`pip3 install -r requirements.txt`.

Ini akan menginstal semua paket python yang diperlukan.

### Database

#### MongoDB

[MongoDB] (https://cloud.mongodb.com/) di sini digunakan untuk menyimpan pengguna, obrolan, status afk, daftar hitam, larangan global, data.

#### SQL

Jika Anda ingin menggunakan modul yang bergantung pada database (misalnya: kunci, catatan, filter, selamat datang),
Anda harus memiliki database yang terpasang di sistem Anda. Saya menggunakan Postgres, jadi saya sarankan menggunakannya untuk kompatibilitas optimal.

Dalam kasus Postgres, inilah cara Anda mengatur database pada sistem Debian / Ubuntu. Distribusi lain mungkin berbeda.

- instal PostgreSQL:

`sudo apt-get update && sudo apt-get install postgresql`

- ubah ke pengguna Postgres:

`sudo su - postgres`

- buat pengguna database baru (ubah YOUR_USER dengan benar):

`createuser -P -s -e YOUR_USER`

Ini akan diikuti oleh Anda perlu memasukkan kata sandi Anda.

- buat tabel database baru:

`Createdb -O YOUR_USER YOUR_DB_NAME`

Ubah YOUR_USER dan YOUR_DB_NAME dengan benar.

- akhirnya:

`psql YOUR_DB_NAME -h YOUR_HOST YOUR_USER`

Ini akan memungkinkan Anda untuk terhubung ke database Anda melalui terminal Anda.
Secara default, YOUR_HOST harus 0.0.0.0:5432.

Anda sekarang harus dapat membangun URI database Anda. Ini akan menjadi:

`sqldbtype://username:pw@hostname:port/db_name`

Ganti SqlDbType dengan DB mana pun yang Anda gunakan (mis. Postgres, MySQL, SQLite, dll)
ulangi untuk nama pengguna, kata sandi, nama host (localhost?), port (5432?), dan nama DB Anda.

## Modules

### Setting load order

Urutan pemuatan modul dapat diubah melalui pengaturan konfigurasi `LOAD` dan` NO_LOAD`.
Keduanya harus mewakili daftar.

Jika `LOAD` adalah daftar kosong, semua modul dalam` modules / `akan dipilih untuk dimuat secara default.

Jika `NO_LOAD` tidak ada atau merupakan daftar kosong, semua modul yang dipilih untuk dimuat akan dimuat.

Jika modul ada di `LOAD` dan` NO_LOAD`, modul tidak akan dimuat - `NO_LOAD` diprioritaskan.

### Membuat modul Anda sendiri

Membuat modul telah disederhanakan semaksimal mungkin - tetapi jangan ragu untuk menyarankan penyederhanaan lebih lanjut.

Yang diperlukan hanyalah file .py Anda ada di folder modul.

Untuk menambahkan perintah, pastikan untuk mengimpor petugas operator melalui

`from kaga import dispatcher`.

Anda kemudian dapat menambahkan perintah menggunakan biasa

`dispatcher.add_handler()`.

Menetapkan variabel `__help__` ke string yang menjelaskan ketersediaan modul ini
perintah akan memungkinkan bot memuatnya dan menambahkan dokumentasinya
modul Anda ke perintah `/help`. Menyetel variabel `__mod_name__` juga akan memungkinkan Anda menggunakan variabel yang lebih bagus,
nama yang mudah digunakan untuk modul.

Fungsi `__migrate __ ()` digunakan untuk memigrasi obrolan - saat obrolan ditingkatkan ke supergrup, ID berubah, jadi
perlu untuk memigrasikannya di DB.

Fungsi `__stats__ ()` adalah untuk mengambil statistik modul, misalnya jumlah pengguna, jumlah obrolan. Ini diakses
melalui perintah `/stats`, yang hanya tersedia untuk pemilik bot.
