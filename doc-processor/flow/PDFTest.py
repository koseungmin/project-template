# test.py
import uuid

from PDFGenerator import PDFGenerator


def main():
    # PDFGenerator 인스턴스 생성
    pdf_gen = PDFGenerator(font_size=8)

    # 페이지별 텍스트 추가
    pdf_gen.add_page("1️⃣ 첫 번째 페이지입니다.\n이 페이지는 테스트를 위한 첫 페이지입니다."*20)
    pdf_gen.add_page("2️⃣ 두 번째 페이지입니다.\n여러 줄의 텍스트가 포함됩니다.\n이것은 줄바꿈 예제입니다."*20)
    pdf_gen.add_page("3️⃣ 세 번째 페이지입니다.\n마지막 테스트 페이지입니다.\nPDF가 잘 생성되는지 확인하세요!"*20)

    # 전체 페이지 PDF 생성
    unique_pdf = uuid.uuid4().hex
    # pdf_gen.generate("./extracted_pdf/test_full.pdf")
    pdf_gen.generate("./extracted_pdf/"+unique_pdf+".pdf")

    # 특정 페이지만 생성 (예: 1, 3페이지)
    unique_pdf2 = uuid.uuid4().hex
    # pdf_gen.generate("./extracted_pdf/test_partial.pdf", pages=[1, 3])
    pdf_gen.generate("./extracted_pdf/"+unique_pdf2+".pdf", pages=[1, 3])

if __name__ == "__main__":
    main()
