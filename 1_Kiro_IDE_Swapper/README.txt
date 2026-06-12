==========================================================
 TOOL 1 — KIRO IDE SWAPPER
 Doi nhanh account Kiro IDE bang file JSON (1 click)
==========================================================

CHUC NANG
  - Hien account dang login Kiro IDE (provider, han su dung, profile).
  - Inject 1 file JSON -> kill Kiro.exe -> mo lai = login luon account do.
  - Nhan ca 3 loai file:
      * kiro-auth-token.json  (dict)            -> dung truc tiep
      * cookie export tu app.kiro.dev (array)   -> tu build roi swap
      * JSON IDC/durable tu Tool 2 (array)      -> build + ghi them OIDC
        registration de Kiro IDE tu refresh token (dung lau dai)
  - Backup account dang login de dung lai sau.

YEU CAU
  - Windows + da cai Kiro IDE (mac dinh: %LOCALAPPDATA%\Programs\Kiro\Kiro.exe)
  - Python 3.10+  (tai tai https://www.python.org, nho tick "Add to PATH")

CAI DAT (chi lan dau)
  - Bam dup  CAI_DAT.bat

CHAY
  - Bam dup  RUN.bat

CACH DUNG
  1. (Tuy chon) Bam "Backup account dang login..." de luu account hien tai.
  2. Keo-tha file JSON vao o xanh, HOAC bam "Swap file JSON..." chon file,
     HOAC bo file vao folder "accounts" roi Scan -> Chon -> SWAP.
  3. Tool tu tat Kiro -> ghi token -> mo lai. NHO LUU CONG VIEC TRUOC KHI SWAP.

LUU Y
  - Backup tu dong account cu thanh _previous_<time>.kiro-auth-token.json.
  - Bo tick "Mo lai Kiro" neu khong muon tool tu mo Kiro.

----------------------------------------------------------
 NGON NGU / LANGUAGE / 语言
----------------------------------------------------------
  Doi ngon ngu o goc tren ben phai: Tieng Viet / English / 中文
  README: README.txt (VI) | README.en.txt | README.zh.txt
