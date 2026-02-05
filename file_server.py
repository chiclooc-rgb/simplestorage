import streamlit as st
import os
from pathlib import Path
from datetime import datetime

# 설정
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="파일 저장소", page_icon="📁", layout="wide")

st.title("📁 파일 저장소")

# 파일 업로드 섹션
st.header("파일 업로드")
uploaded_files = st.file_uploader(
    "파일을 선택하세요",
    accept_multiple_files=True,
    help="여러 파일을 한 번에 업로드할 수 있습니다"
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_path = UPLOAD_DIR / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ {uploaded_file.name} 업로드 완료!")

st.divider()

# 파일 목록 섹션
st.header("저장된 파일")

files = list(UPLOAD_DIR.iterdir())
if not files:
    st.info("업로드된 파일이 없습니다.")
else:
    # 파일 정렬 (최신순)
    files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)

    for file_path in files:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

        with col1:
            st.write(f"📄 **{file_path.name}**")

        with col2:
            # 파일 크기 표시
            size = file_path.stat().st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            st.caption(f"{size_str} | {mtime.strftime('%Y-%m-%d %H:%M')}")

        with col3:
            # 다운로드 버튼
            with open(file_path, "rb") as f:
                st.download_button(
                    label="⬇️ 다운로드",
                    data=f.read(),
                    file_name=file_path.name,
                    key=f"download_{file_path.name}"
                )

        with col4:
            # 삭제 버튼
            if st.button("🗑️ 삭제", key=f"delete_{file_path.name}"):
                file_path.unlink()
                st.rerun()

        # 미리보기
        suffix = file_path.suffix.lower()

        # 이미지 미리보기
        if suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
            with st.expander("🖼️ 미리보기"):
                st.image(str(file_path), use_container_width=True)

        # 텍스트 미리보기
        elif suffix in [".txt", ".md", ".py", ".json", ".csv", ".html", ".css", ".js"]:
            with st.expander("📝 미리보기"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if suffix == ".md":
                        st.markdown(content)
                    elif suffix == ".csv":
                        import pandas as pd
                        df = pd.read_csv(file_path)
                        st.dataframe(df)
                    else:
                        st.code(content, language=suffix[1:] if suffix[1:] in ["py", "json", "html", "css", "js"] else None)
                except Exception as e:
                    st.error(f"미리보기 실패: {e}")

        # PDF 미리보기 안내
        elif suffix == ".pdf":
            with st.expander("📑 PDF 파일"):
                st.info("PDF 파일은 다운로드 후 확인해주세요.")

        st.divider()

# 사이드바에 정보 표시
with st.sidebar:
    st.header("ℹ️ 정보")
    st.write(f"**저장 위치:** `{UPLOAD_DIR.absolute()}`")
    st.write(f"**파일 개수:** {len(files)}개")

    total_size = sum(f.stat().st_size for f in files) if files else 0
    if total_size < 1024 * 1024:
        st.write(f"**총 용량:** {total_size / 1024:.1f} KB")
    else:
        st.write(f"**총 용량:** {total_size / (1024 * 1024):.1f} MB")
