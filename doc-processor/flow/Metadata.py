from typing import Dict, List


def process_file_metadata(file_list: List[str], metadata_list: List[Dict]) -> List[Dict]:
    """
    외부에서 전달된 파일 리스트와 파일 메타데이터 리스트를 받아 처리하는 함수.

    Args:
        file_list (list[str]): 파일 경로 리스트
        metadata_list (list[dict]): 파일 메타데이터 리스트 (각 dict에 filename 키가 포함되어야 함)

    Returns:
        list[dict]: 각 파일별 매칭된 메타데이터 결과 리스트
    """

    results = []

    for file_path in file_list:
        file_name = file_path.split("/")[-1]  # 파일명만 추출
        # filename 키를 기준으로 메타데이터 매칭
        meta_info = next((m for m in metadata_list if m.get("filename") == file_name), None)

        if meta_info:
            results.append({
                "file": file_path,
                "size_bytes": meta_info.get("size_bytes"),
                "modified_time": meta_info.get("modified_time"),
                "created_time": meta_info.get("created_time"),
                "status": "found"
            })
        else:
            results.append({
                "file": file_path,
                "status": "not_found"
            })

    return results


# ===== 사용 예시 =====
if __name__ == "__main__":
    # 외부에서 전달된 파일 리스트
    file_list = [
        "./data/sample1.txt",
        "./data/sample2.txt",
        "./data/missing.txt"
    ]

    # 외부에서 전달된 메타데이터 리스트
    metadata_list = [
        {
            "filename": "sample1.txt",
            "size_bytes": 2048,
            "modified_time": "2025-10-21T10:15:00",
            "created_time": "2025-10-20T09:00:00"
        },
        {
            "filename": "sample2.txt",
            "size_bytes": 1024,
            "modified_time": "2025-10-21T09:45:00",
            "created_time": "2025-10-19T12:00:00"
        }
    ]

    result = process_file_metadata(file_list, metadata_list)

    # 보기 좋게 출력
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
