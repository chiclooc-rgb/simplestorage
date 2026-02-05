import streamlit as st
import io
import uuid
from datetime import datetime
from supabase import create_client
from urllib.parse import quote

# 설정
SUPABASE_URL = st.secrets.get("supabase", {}).get("url", "https://dwopbzbjrhnfkwewtwuy.supabase.co")
SUPABASE_KEY = st.secrets.get("supabase", {}).get("key", "")
BUCKET_NAME = "files"

st.set_page_config(page_title="파일 저장소", page_icon="📁", layout="wide")

# CSS로 여백 최소화 - 빽빽하게
st.markdown("""
<style>
    /* 모든 요소 여백 최소화 */
    .stMarkdown {
        margin-bottom: 0 !important;
        margin-top: 0 !important;
        padding: 0 !important;
    }
    /* divider 여백 최소화 */
    hr {
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
    }
    /* 버튼 여백 최소화 */
    .stButton {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .stButton > button {
        padding: 0.25rem 0.5rem !important;
        height: 2rem !important;
    }
    /* 다운로드 버튼 */
    .stDownloadButton {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .stDownloadButton > button {
        padding: 0.25rem 0.5rem !important;
        height: 2rem !important;
    }
    /* 전체 패딩 최소화 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
    }
    /* 컬럼 간격 최소화 */
    [data-testid="column"] {
        padding: 0 0.1rem !important;
    }
    /* 행 간격 최소화 */
    .row-widget {
        margin-bottom: 0 !important;
    }
    /* caption 여백 제거 */
    .stCaption {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def list_files(client):
    """버킷 내 파일 목록 조회"""
    response = client.storage.from_(BUCKET_NAME).list()
    return response


def upload_file(client, file_name, file_data, mime_type):
    """파일 업로드"""
    client.storage.from_(BUCKET_NAME).upload(
        file_name,
        file_data,
        {"content-type": mime_type}
    )


def download_file(client, file_name):
    """파일 다운로드"""
    response = client.storage.from_(BUCKET_NAME).download(file_name)
    return response


def delete_file(client, file_name):
    """파일 삭제"""
    client.storage.from_(BUCKET_NAME).remove([file_name])


def get_file_url(client, file_name):
    """파일 공개 URL 가져오기"""
    return client.storage.from_(BUCKET_NAME).get_public_url(file_name)


# 메인 앱
st.title("📁 파일 저장소")

try:
    client = get_supabase_client()
except Exception as e:
    st.error(f"Supabase 연결 실패: {e}")
    st.stop()

# 파일 업로드 섹션
st.header("파일 업로드")
uploaded_files = st.file_uploader(
    "파일을 선택하세요",
    accept_multiple_files=True,
    help="여러 파일을 한 번에 업로드할 수 있습니다"
)

if uploaded_files:
    if "uploaded" not in st.session_state:
        st.session_state.uploaded = set()

    for uploaded_file in uploaded_files:
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        if file_key not in st.session_state.uploaded:
            try:
                original_name = uploaded_file.name
                # 원본파일명을 base64로 인코딩해서 저장 (파일명__인코딩된원본명.확장자)
                import base64
                encoded_name = base64.urlsafe_b64encode(original_name.encode('utf-8')).decode('ascii')
                ext = original_name.split(".")[-1] if "." in original_name else ""
                safe_name = f"{uuid.uuid4().hex}__{encoded_name}.{ext}" if ext else f"{uuid.uuid4().hex}__{encoded_name}"

                upload_file(client, safe_name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")
                st.success(f"✅ {original_name} 업로드 완료!")
                st.session_state.uploaded.add(file_key)
            except Exception as e:
                st.error(f"❌ {uploaded_file.name} 업로드 실패: {e}")

st.divider()

# 파일 목록 섹션
st.header("저장된 파일")

try:
    files = list_files(client)
except Exception as e:
    st.error(f"파일 목록 조회 실패: {e}")
    files = []

# .emptyFolderPlaceholder 제외
files = [f for f in files if f.get("name") != ".emptyFolderPlaceholder"]

if not files:
    st.info("업로드된 파일이 없습니다.")
else:
    # 최신 파일 먼저
    files = sorted(files, key=lambda x: x.get("created_at", ""), reverse=True)

    for file in files:
        file_name = file.get("name", "")
        # 원본 파일명 복원
        import base64
        if "__" in file_name:
            try:
                encoded_part = file_name.split("__")[1]
                # 확장자 제거
                if "." in encoded_part:
                    encoded_part = encoded_part.rsplit(".", 1)[0]
                display_name = base64.urlsafe_b64decode(encoded_part.encode('ascii')).decode('utf-8')
            except:
                display_name = file_name
        else:
            display_name = file_name

        # 미리보기 가능 여부 확인
        file_lower = display_name.lower()
        has_preview = (
            any(file_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]) or
            any(file_lower.endswith(ext) for ext in [".txt", ".md", ".py", ".json", ".csv", ".html", ".css", ".js"]) or
            file_lower.endswith(".pdf")
        )

        # 컬럼 구성: 파일명 | 정보 | 다운로드 | 삭제 | 미리보기
        if has_preview:
            col1, col2, col3, col4, col5 = st.columns([4, 2, 1, 1, 1])
        else:
            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])

        with col1:
            st.markdown(f"<p style='margin:0; padding:0;'>📄 <b>{display_name}</b></p>", unsafe_allow_html=True)

        with col2:
            size = file.get("metadata", {}).get("size", 0)
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            created = file.get("created_at", "")[:10]
            st.markdown(f"<p style='margin:0; padding:0; font-size:0.8rem; color:gray;'>{size_str} | {created}</p>", unsafe_allow_html=True)

        with col3:
            try:
                file_data = download_file(client, file_name)
                st.download_button(
                    label="⬇️ 다운로드",
                    data=file_data,
                    file_name=display_name,
                    key=f"download_{file_name}",
                    use_container_width=True
                )
            except:
                st.button("⬇️ 다운로드", disabled=True, key=f"download_{file_name}", use_container_width=True)

        with col4:
            if st.button("🗑️ 삭제", key=f"delete_{file_name}", use_container_width=True):
                try:
                    delete_file(client, file_name)
                    st.cache_resource.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제 실패: {e}")

        # 미리보기 버튼
        if has_preview:
            with col5:
                preview_key = f"preview_{file_name}"
                if preview_key not in st.session_state:
                    st.session_state[preview_key] = False

                if st.button("🖼️ 미리보기", key=preview_key + "_btn", use_container_width=True):
                    st.session_state[preview_key] = not st.session_state[preview_key]

        # 미리보기 내용 표시
        if has_preview and st.session_state.get(f"preview_{file_name}", False):
            if any(file_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]):
                try:
                    img_data = download_file(client, file_name)
                    st.image(img_data, use_container_width=True)
                except:
                    st.error("미리보기 실패")

            elif any(file_lower.endswith(ext) for ext in [".txt", ".md", ".py", ".json", ".csv", ".html", ".css", ".js"]):
                try:
                    text_data = download_file(client, file_name).decode("utf-8")
                    if file_lower.endswith(".md"):
                        st.markdown(text_data)
                    elif file_lower.endswith(".csv"):
                        import pandas as pd
                        df = pd.read_csv(io.StringIO(text_data))
                        st.dataframe(df, use_container_width=True)
                    else:
                        ext = file_lower.split(".")[-1]
                        st.code(text_data, language=ext if ext in ["py", "json", "html", "css", "js"] else None)
                except Exception as e:
                    st.error(f"미리보기 실패: {e}")

            elif file_lower.endswith(".pdf"):
                st.info("PDF 파일은 다운로드 후 확인해주세요.")

        st.markdown("<hr style='margin:0.3rem 0; border:0; border-top:1px solid #ddd;'>", unsafe_allow_html=True)

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 정보")
    st.write(f"**파일 개수:** {len(files)}개")

    total_size = sum(f.get("metadata", {}).get("size", 0) for f in files)
    if total_size < 1024 * 1024:
        st.write(f"**총 용량:** {total_size / 1024:.1f} KB")
    else:
        st.write(f"**총 용량:** {total_size / (1024 * 1024):.1f} MB")

    st.caption("Supabase Storage 연동")
