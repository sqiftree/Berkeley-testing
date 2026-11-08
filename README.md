# Berkeley Lab — Kelompok 8

Program Tugas 2 Sistem Terdistribusi: sinkronisasi jam menggunakan **Algoritma Berkeley**.
Pengumpulan/presentasi: **Senin, 9 November 2026**.

Dashboard berbahasa Indonesia, satu perintah untuk demo, tanpa `pip install`.
Client adalah proses Python terpisah yang berkomunikasi melalui TCP; jam yang
diselaraskan adalah **jam virtual**, bukan jam sistem operasi.

## Cara paling mudah (satu laptop)

1. Siapkan **Python 3.9 atau lebih baru**. Cek dengan `python --version` (Windows)
   atau `python3 --version` (Linux/macOS). Jika belum tersedia, instal dari
   [python.org](https://www.python.org/downloads/). Di Windows aktifkan opsi menambahkan Python ke PATH.
2. Buka folder proyek ini. Windows: klik dua kali **`mulai.bat`**.
   Linux/macOS: buka terminal di folder ini lalu jalankan `sh mulai.sh`.
3. Browser membuka **http://127.0.0.1:8000**. Jika tidak terbuka otomatis, ketik alamat itu sendiri.
4. Klik **Sinkronkan sekarang**. Amati selisih jam mengecil dan lihat tabel koreksi.
5. Pilih skenario **Outlier**, klik **Terapkan / ulangi**, lalu sinkronkan lagi.
6. Selesai: tekan **Ctrl+C di terminal**. Menutup tab browser saja tidak menghentikan program.

Alternatif dari terminal:

```bash
# Windows
python app.py

# Linux/macOS
python3 app.py
```

Satu perintah ini otomatis menjalankan 1 koordinator, 3 proses client dengan port
TCP bebas, dan server dashboard lokal. Browser modern seperti Chrome, Edge, atau
Firefox diperlukan. Semua aset lokal; demo tidak membutuhkan internet.

## WSL dengan Docker

Untuk pengguna WSL yang biasa memakai Docker, tersedia peluncur terpisah.
Teman yang memakai Windows langsung tetap cukup menjalankan **`mulai.bat`**
dengan Python terpasang; tidak perlu Docker.

1. Pastikan `docker info` dan `docker compose version` berhasil di terminal WSL.
   Jika memakai Docker Desktop, jalankan Docker Desktop dan aktifkan distro WSL
   di **Settings → Resources → WSL Integration**. Lihat
   [panduan resmi Docker WSL](https://docs.docker.com/desktop/features/wsl/).
   Jika sudah memakai Docker Engine langsung di WSL, cukup pastikan daemon berjalan.
2. Masuk ke folder proyek di terminal WSL, lalu:

   ```bash
   sh mulai-docker.sh
   ```

3. Setelah log menampilkan `Buka http://127.0.0.1:8000`, buka
   **http://localhost:8000** dari browser Windows. Browser tidak dibuka otomatis
   dari dalam container.
4. Tekan **Ctrl+C** untuk berhenti. Untuk menghapus container dan jaringan demo:

   ```bash
   docker compose down
   ```

Image berisi Python, dashboard, koordinator, dan tiga proses client TCP otomatis
dalam satu container. Python di Windows/WSL tidak perlu diinstal untuk mode ini.
Build pertama membutuhkan internet untuk mengambil image Python; setelah image
tersedia, demo dapat berjalan offline.

Perintah Docker langsung (tanpa peluncur):

```bash
docker compose up --build
# Atau jalankan di background:
docker compose up --build -d
docker compose logs -f
# Hentikan mode background:
docker compose down
```

Jika port 8000 sudah dipakai, jalankan `BERKELEY_PORT=8080 sh mulai-docker.sh`,
lalu buka **http://localhost:8080**. Dashboard bind ke `0.0.0.0` di dalam container
agar port forwarding berfungsi; Docker hanya menerbitkan port pada loopback host.
Mode standar `mulai.bat` / `mulai.sh` tetap memakai `127.0.0.1`.

Uji dari image Docker:

```bash
docker compose run --rm --no-deps berkeley python -m unittest discover -s tests -v
docker compose run --rm --no-deps berkeley python tests/smoke_demo.py
```

## Apa yang perlu dilihat?

| Bagian | Makna |
|---|---|
| Jam koordinator | Jam virtual yang dipakai sebagai acuan menghitung offset |
| Offset client | Selisih jam terhadap koordinator; positif berarti lebih cepat |
| Rentang selisih | Offset terbesar dikurangi terkecil, termasuk koordinator 0 |
| RTT | Durasi permintaan dan balasan TCP, termasuk overhead koneksi |
| Koreksi | Nilai yang ditambahkan ke jam virtual komputer tersebut |
| Outlier | Client dengan selisih absolut lebih dari 120 detik dari koordinator |

Nilai tampilan diperbarui setiap 2 detik. Tabel menyimpan hasil putaran terakhir,
sedangkan kartu jam memperlihatkan pengukuran terbaru. Memilih skenario saja belum
mengubah jam: klik **Terapkan / ulangi**. Tombol ini juga menghapus riwayat putaran.

## Cara kerja algoritma

1. Koordinator meminta waktu setiap client melalui TCP.
2. Client membalas timestamp jam virtualnya.
3. Koordinator mengukur RTT memakai jam monotonic. Dengan asumsi perjalanan
   pergi dan pulang relatif simetris, estimasi jam client saat balasan diterima:
   `timestamp_client + RTT / 2`.
4. Offset diukur terhadap jam koordinator **pada saat balasan diterima**:
   `offset_client = timestamp_client + RTT / 2 - waktu_koordinator`.
5. Rata-ratakan offset client yang lolos ambang bersama offset koordinator, yaitu 0:
   `rata_rata = (0 + jumlah_offset_terpilih) / (1 + jumlah_client_terpilih)`.
6. Kirim **koreksi individual**, bukan timestamp bersama:
   `koreksi_client = rata_rata - offset_client`.
   Koordinator sendiri menambahkan `rata_rata` ke jam virtualnya.
7. Client menerapkan koreksi. Client outlier tetap dikoreksi tetapi tidak ikut
   menentukan rata-rata. Client offline dilewati; kegagalan mengirim koreksi ditampilkan.

### Contoh angka

Misalkan koordinator menunjukkan 10:00:00 pada suatu titik acuan:

| Komputer | Jam awal | Offset | Koreksi | Jam hasil ideal pada titik acuan yang sama |
|---|---|---:|---:|---|
| Koordinator | 10:00:00 | 0 dtk | +11,25 dtk | 10:00:11,25 |
| Client 1 | 10:00:20 | +20 dtk | −8,75 dtk | 10:00:11,25 |
| Client 2 | 09:59:50 | −10 dtk | +21,25 dtk | 10:00:11,25 |
| Client 3 | 10:00:35 | +35 dtk | −23,75 dtk | 10:00:11,25 |

Rata-rata = `(0 + 20 - 10 + 35) / 4 = 11,25 detik`.
Saat program berjalan, jam terus maju, jadi tampilan bukan timestamp yang dibekukan.
Untuk skenario outlier: `(0 + 20 - 10) / 3 ≈ 3,333 detik`; offset +300 dikeluarkan
dari rata-rata, lalu client itu mendapat koreksi sekitar −296,667 detik.

Berkeley menghasilkan **sinkronisasi internal**: kesepakatan jam dalam kelompok,
bukan jaminan jam sesuai UTC. Lihat materi [Rutgers tentang sinkronisasi jam](https://people.cs.rutgers.edu/~pxk/classes/417/notes/clocks.html).

## Pengujian terdistribusi pada beberapa laptop

Mode ini menghubungkan koordinator dan client pada perangkat yang berbeda
melalui jaringan TCP. Peluncur `mulai.bat`, `mulai.sh`, dan `mulai-docker.sh`
secara default menjalankan tiga client lokal. Untuk pengujian antarlaptop,
jalankan `node.py` pada perangkat client dan tentukan alamat client melalui
opsi `--clients` pada koordinator.

### 1. Persiapan perangkat dan jaringan

- Hubungkan seluruh perangkat ke jaringan Wi-Fi atau LAN yang sama dan pastikan
  jaringan mengizinkan komunikasi antarperangkat.
- Siapkan source code versi terbaru pada setiap perangkat.
- Tentukan satu perangkat sebagai koordinator. Koordinator dapat berjalan
  langsung dengan Python atau melalui Docker di WSL.
- Siapkan Python 3.9 atau lebih baru pada setiap perangkat client Windows.
  Docker tidak diperlukan pada perangkat client.
- Izinkan koneksi masuk TCP port `9101` pada firewall perangkat client untuk
  jaringan privat yang digunakan dalam pengujian.

Pengujian dapat dilakukan dengan satu hingga tiga perangkat client.
Protokol demonstrasi ini tidak menggunakan autentikasi atau enkripsi;
gunakan jaringan praktikum tepercaya, bukan internet publik.

### 2. Menjalankan layanan client pada Windows

Buka PowerShell atau Command Prompt pada folder proyek di setiap perangkat
client. Jalankan perintah sesuai peran perangkat:

| Perangkat | Perintah |
|---|---|
| Client 1 | `py -3 node.py --host 0.0.0.0 --port 9101 --offset 20` |
| Client 2 | `py -3 node.py --host 0.0.0.0 --port 9101 --offset -10` |
| Client 3 | `py -3 node.py --host 0.0.0.0 --port 9101 --offset 35` |

Jika Python Launcher (`py`) tidak tersedia, gunakan `python` sebagai penggantinya.
Pada Linux/macOS, gunakan `python3`. Terminal client harus tetap terbuka selama
pengujian. Port `9101` dapat digunakan pada seluruh client karena masing-masing
berjalan pada perangkat berbeda. `mulai.bat` tidak diperlukan dalam peran client.

### 3. Mengidentifikasi alamat jaringan client

Jalankan perintah berikut pada setiap perangkat client Windows:

```powershell
ipconfig
```

Catat **IPv4 Address** pada adaptor Wi-Fi atau Ethernet yang terhubung ke jaringan
pengujian. Gunakan alamat adaptor tersebut, bukan alamat loopback `127.0.0.1`
atau alamat adaptor virtual Docker/WSL. Contoh pemetaan perangkat:

| Perangkat | Alamat IPv4 contoh | Endpoint TCP |
|---|---|---|
| Client 1 | `192.168.1.11` | `192.168.1.11:9101` |
| Client 2 | `192.168.1.12` | `192.168.1.12:9101` |
| Client 3 | `192.168.1.13` | `192.168.1.13:9101` |

**Seluruh alamat contoh harus diganti dengan alamat IPv4 aktual perangkat client.**
Koordinator memulai koneksi ke setiap client; alamat koordinator tidak perlu
dimasukkan pada perintah client.

### 4. Menjalankan koordinator

Pilih salah satu metode berikut sesuai lingkungan koordinator.

#### Docker di WSL

Hentikan demo lokal yang masih berjalan dengan **Ctrl+C**. Dari folder proyek
di terminal WSL, bersihkan container demo sebelumnya dan siapkan image:

```bash
docker compose down
docker compose build
```

Untuk pengujian dengan satu perangkat client:

```bash
docker compose run --rm --service-ports berkeley \
  python app.py --host 0.0.0.0 --no-browser \
  --clients 192.168.1.11:9101
```

Untuk pengujian dengan tiga perangkat client:

```bash
docker compose run --rm --service-ports berkeley \
  python app.py --host 0.0.0.0 --no-browser \
  --clients 192.168.1.11:9101 192.168.1.12:9101 192.168.1.13:9101
```

Opsi `--service-ports` menerbitkan port dashboard sesuai `compose.yaml`.
Opsi `--clients` menggantikan client lokal otomatis dengan endpoint perangkat
client yang ditentukan. Buka **http://localhost:8000** pada browser Windows
di perangkat koordinator.

Jika port 8000 digunakan aplikasi lain, tambahkan `BERKELEY_PORT=8080` sebelum
`docker compose run`, kemudian akses **http://localhost:8080**.

#### Python langsung pada Windows

Dari folder proyek pada perangkat koordinator, jalankan:

```powershell
py -3 app.py --clients 192.168.1.11:9101 192.168.1.12:9101 192.168.1.13:9101
```

Untuk satu client, cantumkan satu endpoint setelah `--clients`. Pada Linux/macOS,
gunakan `python3`. Dashboard tersedia di **http://127.0.0.1:8000**.

Dashboard hanya perlu dibuka pada perangkat koordinator. Perangkat client
menjalankan layanan TCP dan tidak perlu membuka dashboard.

### 5. Verifikasi dan skenario pengujian

1. Pastikan indikator jaringan menunjukkan **1/1 client online** atau
   **3/3 client online**, sesuai jumlah endpoint yang dikonfigurasi.
2. Catat offset awal setiap client, lalu pilih **Sinkronkan sekarang**.
   Pastikan koreksi diterapkan dan offset terhadap koordinator mendekati nol.
3. Untuk pengujian tiga client, pilih skenario **Outlier**, kemudian tekan
   **Terapkan / ulangi** dan **Sinkronkan sekarang**. Client dengan offset
   di luar ambang dikeluarkan dari perhitungan rata-rata tetapi tetap dikoreksi.
4. Untuk pengujian kegagalan koneksi, hentikan salah satu layanan client dengan
   **Ctrl+C**. Pastikan dashboard menandainya offline. Jika masih ada client
   online, sinkronisasi tetap dapat dilakukan pada client yang tersedia.
   Jika seluruh client offline, permintaan sinkronisasi akan ditolak.
5. Jalankan kembali layanan client dengan perintah semula untuk menguji pemulihan
   koneksi. Tunggu pembaruan status dashboard, lalu ulangi sinkronisasi.
6. Setelah pengujian selesai, tekan **Ctrl+C** pada terminal koordinator dan
   seluruh terminal client. Untuk koordinator Docker, jalankan
   `docker compose down` untuk membersihkan jaringan Compose setelah container
   pengujian berhenti.

Nilai `--offset` ditambahkan ke waktu lokal masing-masing perangkat. Apabila
jam sistem antarperangkat sudah berbeda, offset awal yang terukur dapat berbeda
dari nilai 20/−10/35 detik. Tombol skenario juga mengatur offset terhadap waktu
lokal perangkat. Seluruh koreksi hanya berlaku pada jam virtual aplikasi dan
tidak mengubah jam sistem operasi.

### 6. Penanganan kendala koneksi

| Kondisi | Pemeriksaan |
|---|---|
| Client berstatus offline sejak awal | Pastikan layanan `node.py` berjalan, alamat IPv4 dan port sesuai, serta firewall mengizinkan TCP `9101` |
| Seluruh client tidak dapat dijangkau | Periksa konektivitas jaringan, isolasi client pada Wi-Fi, serta rute atau kebijakan VPN yang aktif |
| Dashboard Docker tidak dapat dibuka | Pastikan perintah menggunakan `--service-ports` dan `--host 0.0.0.0`, serta port host tidak digunakan container atau aplikasi lain |
| Alamat client berubah setelah koneksi ulang | Periksa kembali IPv4 adaptor aktif dan jalankan ulang koordinator dengan endpoint terbaru |
| Offset akhir tidak tepat nol | Perbedaan kecil dipengaruhi latensi jaringan dan estimasi RTT; evaluasi selisih setelah sinkronisasi |

## Struktur source code

```text
app.py                 Koordinator, peluncur demo, API dan server dashboard
berkeley.py            Jam virtual dan rumus rata-rata/koreksi
node.py                Server TCP client, protokol JSON per baris
static/index.html      Dashboard dan penjelasan singkat
static/style.css       Tampilan responsif
static/app.js          Kontrol dashboard dan pembaruan data
tests/test_berkeley.py Uji hitungan, TCP, outlier, dan client offline
mulai.bat / mulai.sh   Peluncur untuk pemula
mulai-docker.sh        Peluncur Docker untuk WSL/Linux
Dockerfile            Image Python untuk demo
compose.yaml          Port lokal dan healthcheck Docker
```

## Pengujian

```bash
python -m unittest discover -s tests -v
```

Uji jaringan memakai loopback dan toleransi 50 ms; komputer yang sangat sibuk
dapat melampaui toleransi itu. Port client pada pengujian dipilih otomatis.

## Batasan yang perlu dijelaskan

- Koordinator dipilih manual; belum ada pemilihan ulang ketika koordinator mati.
- Sinkronisasi dipicu tombol, bukan penjadwalan periodik. Klik lagi untuk putaran baru.
- Filter outlier memakai ambang tetap relatif ke koordinator, bukan deteksi Byzantine
  atau algoritma statistik konsensus. Bila koordinator salah jauh, hasil juga dapat buruk.
- Kompensasi RTT/2 hanya perkiraan. Overhead koneksi, pemrosesan, dan delay asimetris
  menghasilkan sisa galat; akurasi sempurna tidak dijanjikan.
- Semua jam virtual berjalan pada laju tetap; belum mensimulasikan drift frekuensi.
- Koreksi langsung (step) dapat memundurkan jam virtual. Sistem produksi dapat memakai
  slewing untuk menghindari waktu mundur.
- Jika sebagian pengiriman gagal, sebagian node mungkin belum sinkron; cek tabel dan ulangi.
- Maksimum 50 hasil putaran disimpan di memori, hilang ketika program ditutup/reset.

## Jika mengalami masalah

| Masalah | Solusi |
|---|---|
| `python` tidak dikenali | Coba `py -3` di Windows atau `python3` di Linux/macOS |
| Port 8000 dipakai | Jalankan `python app.py --port 8080`, buka alamat yang dicetak |
| Browser tidak otomatis terbuka | Buka alamat terminal secara manual |
| Client LAN offline | Periksa IP, terminal client, firewall TCP 9101, dan isolasi Wi-Fi |
| Jam tidak persis sama | Selisih kecil adalah efek delay/estimasi; lihat nilai detiknya |
