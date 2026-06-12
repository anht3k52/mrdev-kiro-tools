==========================================================
 TOOL 2 — AWS AUTO LOGIN  ->  lay JSON durable
==========================================================

CHUC NANG
  - Doc file account (Excel/txt) -> mo Chrome SACH (khong cache) bang Playwright
  - Tu dong dang nhap AWS IAM Identity Center:
      * Account moi (lan dau)  -> TU DOI MAT KHAU (mat khau moi o o cau hinh)
      * Account da doi pass     -> dang nhap binh thuong
    (Tool tu nhan dien, khong can chon che do)
  - Sau khi login -> xuat JSON DURABLE day du (refresh_token + client_id +
    client_secret + profileArn). Chay HANG LOAT + DA LUONG.
  - KHONG dong vao 9router (viec do dung Tool 3).

YEU CAU
  - Windows + Python 3.10+ (tick "Add to PATH" khi cai Python)

CAI DAT (chi lan dau)
  - Bam dup  CAI_DAT.bat   (cai thu vien + tai trinh duyet Chromium ~150MB)

CHAY
  - Bam dup  RUN.bat

DINH DANG FILE ACCOUNT
  - Excel (.xlsx): cot A = Email/Username, cot B = Password  (tu dong 2)
  - Text (.txt):   moi dong  "email:password"  (username thuan cung duoc)
      vi du:
         user01:MatKhauTam123
         user02|MatKhauTam456
  - Tool tu GHI mat khau moi + ket qua vao file sau khi chay (lan sau chay lai dung).

CACH DUNG
  1. Chon file account.
  2. Chon thu muc xuat JSON (mac dinh: output_json).
  3. Chinh "Luong song song" (3-5 la hop ly), "Mat khau moi", IDC start URL neu khac.
     Da doi pass roi: tick "Ghi de password trong file" + nhap mat khau hien tai.
  4. Chon "Kiro region" — EU workspace: eu-central-1 (mac dinh), US: us-east-1.
  5. Bam "BAT DAU AUTO LOGIN". Xem log chay.

LUU Y KIRO REGION
  - Day la endpoint Kiro/Q (q.REGION.amazonaws.com), KHONG phai AWS account region.
  - JSON cu sai region (us-east-1) -> chay lai Tool 2 HOAC:
      python fix_kiro_region.py output_json
  - 9router: sau inject, kiem tra provider Kiro co "region": "eu-central-1" trong DB.
    Neu sai: xoa connection cu, inject lai JSON moi, restart 9router.

LUU Y
  - Account khong co MFA/2FA thi login 100% tu dong.
  - Neu account bi AWS nghi ngo (sai pass nhieu lan) se hien CAPTCHA -> TAT
    "Headless" de tu giai tay, hoac dung account khac.
  - Chay nhieu luong qua se nang CPU -> de 3-5 luong.

----------------------------------------------------------
 BAN .EXE (khong can cai Python)
----------------------------------------------------------
  Tool 2 ban exe la 1 THU MUC (vi playwright can kem trinh duyet Chromium).
  - Chay: vao thu muc -> bam dup Tool2_AWS_Auto_Login.exe
  - Thu muc "ms-playwright" (Chromium) PHAI nam CANH file .exe (trong cung folder).
  - Gui khach: nen NET/ZIP CA THU MUC.
  (Tu build lai: bam BUILD_EXE.bat)

  CO 2 KIEU BUILD:
   A) BUILD_EXE.bat          -> ban STANDALONE (1 thu muc, nhieu file).
                                Khoi dong nhanh. Gui khach: ZIP CA THU MUC.
   B) BUILD_EXE_ONEFILE.bat  -> ban ONEFILE (DUY NHAT 1 file .exe).
                                Gui 1 file la xong, khong kem folder.
                                Doi lai: file RAT TO (~300-400MB) va lan dau
                                mo se cham (bung Chromium ra thu muc tam).

----------------------------------------------------------
 NGON NGU / LANGUAGE / 语言
----------------------------------------------------------
  Doi ngon ngu o goc tren ben phai: Tieng Viet / English / 中文
  (Change language at top-right dropdown.)
