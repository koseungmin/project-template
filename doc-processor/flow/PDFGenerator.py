import os
import platform

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


class PDFGenerator:
    """운영체제별 디폴트 한글 폰트 지원 PDF 생성기 + 개별 페이지 추가 가능"""

    def __init__(self, font_size=10, margin_mm=10, page_size=A4):
        self.font_size = font_size
        self.margin = margin_mm * mm
        self.page_size = page_size
        self.leading = int(font_size * 1.3)
        self.pages_lines = []  # add_page로 추가할 페이지 저장

        # OS별 폰트 설정
        self.font_name, self.font_path = self._get_default_font()
        self._register_font()

    def _get_default_font(self):
        system = platform.system()
        if system == "Windows":
            # Windows: Malgun Gothic
            return "Malgun Gothic", "C:/Windows/Fonts/malgun.ttf"
        else:
            # Linux: NanumGothic
            return "NanumGothic", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

    def _register_font(self):
        if not os.path.exists(self.font_path):
            raise FileNotFoundError(
                f"폰트 파일을 찾을 수 없습니다: {self.font_path}\n"
                "→ OS에 맞는 TTF 폰트를 설치하거나 경로를 수정하세요."
            )
        if self.font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(self.font_name, self.font_path))
            print(f"✅ 폰트 등록 완료: {self.font_name}")

    def _split_text_into_lines(self, text: str):
        """텍스트를 라인 단위로 나누고 줄바꿈 처리"""
        width, _ = self.page_size
        usable_w = width - 2 * self.margin

        lines = []
        for paragraph in text.splitlines():
            if paragraph.strip() == "":
                lines.append("")
            else:
                wrapped = simpleSplit(paragraph, self.font_name, self.font_size, usable_w)
                lines.extend(wrapped)
        if not lines:
            lines = [""]
        return lines

    def add_page(self, text: str):
        """
        한 페이지씩 추가
        Args:
            text (str): 페이지에 들어갈 텍스트
        """
        lines = self._split_text_into_lines(text)
        self.pages_lines.append(lines)

    def generate(self, filename: str, pages=None):
        """
        PDF 생성
        Args:
            filename (str): 저장할 PDF 파일명
            pages (list[int] | None): 출력할 페이지 번호 (1부터 시작). None이면 전체
        """
        width, height = self.page_size
        total_pages = len(self.pages_lines)
        if pages is None:
            pages_to_render = range(1, total_pages + 1)
        else:
            pages_to_render = [p for p in pages if 1 <= p <= total_pages]

        c = canvas.Canvas(filename, pagesize=self.page_size)

        for i, lines_in_page in enumerate(self.pages_lines, start=1):
            if i not in pages_to_render:
                continue
            y = height - self.margin - self.font_size
            c.setFont(self.font_name, self.font_size)
            for line in lines_in_page:
                c.drawString(self.margin, y, line)
                y -= self.leading
            c.showPage()

        c.save()
        print(f"📘 PDF 생성 완료: {filename} (총 {total_pages}페이지 중 {len(pages_to_render)}페이지 출력됨)")


# ===== 테스트 코드 =====
if __name__ == "__main__":
    sample_text_1 = "첫 번째 페이지 내용입니다.\n줄바꿈 테스트"*20
    sample_text_2 = "두 번째 페이지 내용입니다.\n여기에 더 많은 텍스트를 넣을 수 있습니다."*20
    sample_text_3 = "세 번째 페이지 내용입니다.\n마지막 테스트 페이지입니다."*20

    pdf_gen = PDFGenerator(font_size=8)

    # 개별 페이지 추가
    pdf_gen.add_page(sample_text_1)
    pdf_gen.add_page(sample_text_2)
    pdf_gen.add_page(sample_text_3)

    # 전체 페이지 생성
    pdf_gen.generate("./extracted_pdf/pages_added_full.pdf")

    # 특정 페이지만 생성 (1,3페이지만)
    pdf_gen.generate("./extracted_pdf/pages_added_partial.pdf", pages=[2, 3])
