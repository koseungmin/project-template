"""
파일 저장 카테고리 상수 정의

FileManager.upload() 메서드에서 사용되는 category 매개변수의 값들을
일원화하여 관리하기 위한 상수 클래스입니다.
"""


class FileCategory:
    """파일 저장 카테고리 상수 클래스"""

    # Batch 관련
    BATCH_BP_UPLOAD = "batch/bpupload"

    # Bid 관련
    BID_RFP = "bid/rfp"
    BID_EVAL_FORM = "bid/eval_form"
    BID_PROPOSAL_EVAL = "bid/proposal_eval"
    BID_RFP_EXAMPLE = "bid/rfp_example"
    BID_RFP_TEMPLATE = "bid/rfp_template"

    # BP Source 관련
    BPSOURCE_TRANSACTION = "bpsource/transaction"
    BPSOURCE_SPECIFIC = "bpsource/specific"

    @classmethod
    def get_all_categories(cls) -> list[str]:
        """모든 카테고리 목록 반환"""
        return [
            cls.BATCH_BP_UPLOAD,
            cls.BID_RFP,
            cls.BID_EVAL_FORM,
            cls.BID_PROPOSAL_EVAL,
            cls.BID_RFP_EXAMPLE,
            cls.BID_RFP_TEMPLATE,
            cls.BPSOURCE_TRANSACTION,
            cls.BPSOURCE_SPECIFIC,
        ]

    @classmethod
    def is_valid_category(cls, category: str) -> bool:
        """유효한 카테고리인지 검증"""
        return category in cls.get_all_categories()

    @classmethod
    def get_categories_by_domain(cls, domain: str) -> list[str]:
        """도메인별 카테고리 목록 반환"""
        domain_mapping = {
            "batch": [cls.BATCH_BP_UPLOAD],
            "bid": [
                cls.BID_RFP,
                cls.BID_EVAL_FORM,
                cls.BID_PROPOSAL_EVAL,
                cls.BID_RFP_EXAMPLE,
                cls.BID_RFP_TEMPLATE,
            ],
            "bpsource": [
                cls.BPSOURCE_TRANSACTION,
                cls.BPSOURCE_SPECIFIC,
            ],
        }
        return domain_mapping.get(domain, [])
