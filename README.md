# AI-Access (Universal Assistant System)

Tizim barcha qurilmalar (Windows EXE, Android APK) va web platformalarni yagona sun'iy intellekt ekotizimida birlashtiradi. Sistemada maxfiy API kalitlar xavfsiz holatda markaziy backend serverda saqlanadi, klon ilovalar esa faqat "Device Token" orqali ulanadi (API kalitlar ko'rinmaydi).

## Loyiha Qismlari

Barcha qismlar birgalikda ishlaydi:
1. **`backend/` (Node.js)**: Asosiy "miya". API kalitlarni boshqaradi, AI bilan gaplashadi (Groq, Gemini, GPT-4 fallback tizimi). Screen Analysis'ga ega.
2. **`config-site/` (Next.js)**: Maxsus sozlamalar web-sayti. Bu yerdan siz tokenni kiritib Device Token olasiz va Ilovalarni yulab olasiz (APK/EXE).
3. **`desktop-app/` (Electron + React)**: Kompyuter oynasi. Windows'da yashirin (Background) rejimda ishlashi, Shift tugmasiga ulanishi, ZIP va fayllarga bevosita murojaat eta olishi bilan ajralib turadi. Exam Mode red-text bor.
4. **`mobile-app/` (React Native / Expo)**: Telefon darchasi. Ekrandagi quloqcha (floating icon) ko'rinishida fon qismida doim javob berishga shay.

## GitHub'ga yuklash qoidalari

Siz sistemani GitHub Actions orqali avtomatik Build qilish imkoniyatiga egasiz. Ya'ni, siz faqat kodni yuklaysiz, GitHub serverlari o'zi `.exe` va `.apk` fayllarni "Release" qismida chiqarib beradi.

### 1-qadam: GitHub'ga yuklash
Buning uchun VS Code yoki xohlagan terminalingizda quydagi buyruqlarni yozasiz:
```bash
git add .
git commit -m "First release of AI-Access"
git branch -M main
git remote add origin https://github.com/USERNAME/AI-Access.git
git push -u origin main
```
*`.gitignore` fayli barchasini to'g'ri filtrlab, maxfiy kalitiz bo'lgan `.env` ni va ortiqcha `node_modules` ni u yerga jo'natmaydi.*

### 2-qadam: Avtomatik Build qanday ishlaydi?
Kodni `main` branch'ga yuborganingizdan so'ng, loyihadagi `.github/workflows/` ichidagi fayllar avto-ishga tushadi.
- Windows Action ishlagandan so'ng, Tizim sizga **`AI-Access-Windows-Setup.exe`** ni taqdim etadi.
- Linux/Expo Action ishlagandan so'ng esa, **`AI-Access.apk`** fayli chiqadi.

### 2.1-qadam: Tag orqali release build
`v1.0.0` kabi tag push qilsangiz `release-tag.yml` avtomatik ishga tushadi va bitta GitHub Release ichiga EXE + APK qo'shadi:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 3-qadam: Serverni yurgizish (Backend & Web)
Eng yaxshi yo'l: Render.com ga kirib, GitHub repositoriyni ulaysiz.
1. Backend uchun: `Root directory: backend`, Command: `npm install && node server.js`.
2. Environment Variables qismida o'zingizning Groq/Gemini/HuggingFace API kalitlaringizni kiritib qo'yasiz.

## Xavfsizlik
- Haqiqiy `.env` fayl hech qachon GitHub'ga push qilinmasin.
- Yangi sozlash uchun `backend/.env.example` dan nusxa olib lokal `backend/.env` yarating.
- Agar kalitlar biror joyda ko'rinib qolgan bo'lsa, provider panelidan darhol rotate qiling.

---
**🚀 Tayyor! Endi faqat ilovadan lazzatlaning.**
