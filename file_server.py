import streamlit as st
import io
import json
from datetime import datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# 설정
FOLDER_ID = "1MiUu9OsEBUzUcWFoD005-n89HWLnz5lK"
SCOPES = ["https://www.googleapis.com/auth/drive"]
BASE_DIR = Path(__file__).parent

st.set_page_config(page_title="파일 저장소", page_icon="📁", layout="wide")


def get_oauth_config():
    """OAuth 설정 가져오기"""
    try:
        # Streamlit Cloud: secrets 사용
        return {
            "installed": {
                "client_id": st.secrets["oauth"]["client_id"],
                "client_secret": st.secrets["oauth"]["client_secret"],
                "project_id": st.secrets["oauth"]["project_id"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"]
            }
        }
    except:
        # 로컬: client_secret.json 사용
        creds_path = BASE_DIR / "client_secret.json"
        with open(creds_path, "r") as f:
            return json.load(f)


def get_drive_service():
    """Google Drive API 서비스 생성 (OAuth)"""
    if "credentials" not in st.session_state:
        return None

    creds_data = st.session_state["credentials"]
    creds = Credentials(
        token=creds_data["token"],
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=get_oauth_config()["installed"]["client_id"],
        client_secret=get_oauth_config()["installed"]["client_secret"],
        scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def list_files(service):
    """폴더 내 파일 목록 조회"""
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name, size, createdTime, mimeType)",
        orderBy="createdTime desc"
    ).execute()
    return results.get("files", [])


def upload_file(service, file_name, file_data, mime_type):
    """파일 업로드"""
    file_metadata = {"name": file_name, "parents": [FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mime_type, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields="id").execute()


def download_file(service, file_id):
    """파일 다운로드"""
    request = service.files().get_media(fileId=file_id)
    file_data = io.BytesIO()
    downloader = MediaIoBaseDownload(file_data, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    file_data.seek(0)
    return file_data.read()


def delete_file(service, file_id):
    """파일 삭제"""
    service.files().delete(fileId=file_id).execute()


# 메인 앱
st.title("📁 파일 저장소")

# OAuth 인증 처리
query_params = st.query_params

if "code" in query_params and "credentials" not in st.session_state:
    # OAuth 콜백 처리
    try:
        config = get_oauth_config()
        flow = Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri=st.secrets.get("oauth", {}).get("redirect_uri", "http://localhost:8501")
        )
        flow.fetch_token(code=query_params["code"])
        creds = flow.credentials
        st.session_state["credentials"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token
        }
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"인증 실패: {e}")

# 로그인 상태 확인
service = get_drive_service()

if service is None:
    st.warning("Google Drive에 로그인이 필요합니다.")

    if st.button("🔐 Google 로그인", type="primary"):
        config = get_oauth_config()
        redirect_uri = st.secrets.get("oauth", {}).get("redirect_uri", "http://localhost:8501")
        flow = Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        st.markdown(f"[👉 여기를 클릭하여 로그인]({auth_url})")
    st.stop()

# 로그아웃 버튼
with st.sidebar:
    if st.button("🚪 로그아웃"):
        del st.session_state["credentials"]
        st.rerun()

# 파일 업로드 섹션
st.header("파일 업로드")
uploaded_files = st.file_uploader(
    "파일을 선택하세요",
    accept_multiple_files=True,
    help="여러 파일을 한 번에 업로드할 수 있습니다"
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            upload_file(service, uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")
            st.success(f"✅ {uploaded_file.name} 업로드 완료!")
        except Exception as e:
            st.error(f"❌ {uploaded_file.name} 업로드 실패: {e}")
    st.rerun()

st.divider()

# 파일 목록 섹션
st.header("저장된 파일")

try:
    files = list_files(service)
except Exception as e:
    st.error(f"파일 목록 조회 실패: {e}")
    files = []

if not files:
    st.info("업로드된 파일이 없습니다.")
else:
    for file in files:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

        with col1:
            st.write(f"📄 **{file['name']}**")

        with col2:
            size = int(file.get("size", 0))
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            created = datetime.fromisoformat(file["createdTime"].replace("Z", "+00:00"))
            st.caption(f"{size_str} | {created.strftime('%Y-%m-%d %H:%M')}")

        with col3:
            try:
                file_data = download_file(service, file["id"])
                st.download_button(
                    label="⬇️ 다운로드",
                    data=file_data,
                    file_name=file["name"],
                    key=f"download_{file['id']}"
                )
            except:
                st.button("⬇️ 다운로드", disabled=True, key=f"download_{file['id']}")

        with col4:
            if st.button("🗑️ 삭제", key=f"delete_{file['id']}"):
                try:
                    delete_file(service, file["id"])
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제 실패: {e}")

        # 미리보기
        mime_type = file.get("mimeType", "")
        file_name = file["name"].lower()

        if mime_type.startswith("image/"):
            with st.expander("🖼️ 미리보기"):
                try:
                    img_data = download_file(service, file["id"])
                    st.image(img_data)
                except:
                    st.error("미리보기 실패")

        elif any(file_name.endswith(ext) for ext in [".txt", ".md", ".py", ".json", ".csv", ".html", ".css", ".js"]):
            with st.expander("📝 미리보기"):
                try:
                    text_data = download_file(service, file["id"]).decode("utf-8")
                    if file_name.endswith(".md"):
                        st.markdown(text_data)
                    elif file_name.endswith(".csv"):
                        import pandas as pd
                        df = pd.read_csv(io.StringIO(text_data))
                        st.dataframe(df)
                    else:
                        ext = file_name.split(".")[-1]
                        st.code(text_data, language=ext if ext in ["py", "json", "html", "css", "js"] else None)
                except Exception as e:
                    st.error(f"미리보기 실패: {e}")

        elif file_name.endswith(".pdf"):
            with st.expander("📑 PDF 파일"):
                st.info("PDF 파일은 다운로드 후 확인해주세요.")

        st.divider()

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 정보")
    st.write(f"**파일 개수:** {len(files)}개")

    total_size = sum(int(f.get("size", 0)) for f in files)
    if total_size < 1024 * 1024:
        st.write(f"**총 용량:** {total_size / 1024:.1f} KB")
    else:
        st.write(f"**총 용량:** {total_size / (1024 * 1024):.1f} MB")

    st.caption("Google Drive 연동 (OAuth)")
