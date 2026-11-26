import copy
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import lost_and_found as lost


@pytest.fixture(autouse=True)
def reset_lost_and_found_state():
    """전역 저장소를 초기화하여 테스트 간 상태가 섞이지 않게 한다."""
    lost.items.clear()
    lost.NEXT_NO = 1


def register(name="검정 우산", category="기타", found_date="2026-11-12", location="학생지원팀 보관함"):
    return lost.RegisterItem(name, category, found_date, location, "학생A", "")


# TC-REG-001: 유효한 습득물을 순번 번호와 보관 중 상태로 등록한다.
def test_register_item_assigns_number_and_stored_status_for_valid_input():
    assert register() == "P1"
    assert lost.items == [{
        "no": "P1", "name": "검정 우산", "category": "기타",
        "found_date": "2026-11-12", "location": "학생지원팀 보관함", "status": "보관 중",
    }]


# TC-REG-002: 연속 등록한 물품에는 중복 없는 순번 번호를 부여한다.
def test_register_item_increments_number_without_changing_existing_item():
    register()
    original = copy.deepcopy(lost.items[0])

    assert register("파란 물병", "생활용품", "2026-11-13", "도서관 안내데스크") == "P2"
    assert lost.items[0] == original
    assert lost.items[1]["no"] == "P2"
    assert lost.items[1]["status"] == "보관 중"


# TC-REG-003: 빈 물품명은 등록하지 않고 기존 기록을 보존한다.
def test_register_item_rejects_blank_name_without_changing_state():
    register()
    before = copy.deepcopy(lost.items)

    assert lost.RegisterItem("", "기타", "2026-11-12", "학생지원팀 보관함", "학생A", "") == "물품명을 입력하세요"
    assert lost.items == before
    assert lost.NEXT_NO == 2


# TC-REG-004: None 물품명은 등록하지 않는다.
def test_register_item_rejects_none_name_without_creating_item():
    assert lost.RegisterItem(None, "기타", "2026-11-12", "학생지원팀 보관함", "학생A", "") == "물품명을 입력하세요"
    assert lost.items == []
    assert lost.NEXT_NO == 1


# TC-REG-005: 빈 값 또는 None 분류는 등록하지 않는다.
@pytest.mark.parametrize("category", ["", None])
def test_register_item_rejects_blank_or_none_category(category):
    assert lost.RegisterItem("검정 우산", category, "2026-11-12", "학생지원팀 보관함", "학생A", "") == "분류를 입력하세요"
    assert lost.items == []
    assert lost.NEXT_NO == 1


# TC-REG-006: 빈 습득일은 등록하지 않는다.
def test_register_item_rejects_blank_found_date_without_creating_item():
    response = lost.RegisterItem("검정 우산", "기타", "", "학생지원팀 보관함", "학생A", "")

    assert response == "습득일을 입력하세요"
    assert lost.items == []
    assert lost.NEXT_NO == 1


# TC-REG-007: 달력상 존재하지 않는 습득일은 등록하지 않는다.
def test_register_item_rejects_invalid_found_date_without_creating_item():
    response = lost.RegisterItem("검정 우산", "기타", "2026-02-30", "학생지원팀 보관함", "학생A", "")

    assert response == "올바른 습득일을 입력하세요"
    assert lost.items == []
    assert lost.NEXT_NO == 1


# TC-REG-008: 빈 보관 장소는 등록하지 않는다.
def test_register_item_rejects_blank_location_without_creating_item():
    response = lost.RegisterItem("검정 우산", "기타", "2026-11-12", None, "학생A", "")

    assert response == "보관 장소를 입력하세요"
    assert lost.items == []
    assert lost.NEXT_NO == 1


# TC-SRC-001: 물품명 부분 일치로 보관 중 물품을 조회한다.
def test_search_by_name_returns_matching_stored_item_without_mutation():
    register()
    register("파란 물병", "생활용품")
    before = copy.deepcopy(lost.items)

    assert lost.search_by_name("우산") == ["P1 검정 우산 [기타] 습득일 2026-11-12 / 보관 장소 학생지원팀 보관함"]
    assert lost.items == before


# TC-SRC-002: 분류 부분 일치 결과를 등록 순서대로 반환한다.
def test_search_by_category_returns_matching_items_in_registration_order():
    register()
    register("파란 물병", "생활용품")
    register("빨간 우산", "기타")

    results = lost.search_by_category("기타")

    assert len(results) == 2
    assert results[0].startswith("P1 검정 우산 [기타]")
    assert results[1].startswith("P3 빨간 우산 [기타]")


# TC-SRC-003: 일치 항목이 없으면 빈 목록과 문의 방법을 안내한다.
def test_search_by_name_returns_empty_list_and_contact_guidance_when_no_match(capsys):
    register()
    before = copy.deepcopy(lost.items)

    assert lost.search_by_name("노트북") == []
    assert capsys.readouterr().out.strip() == "검색 결과가 없습니다. 학생지원팀에 문의하세요."
    assert lost.items == before


# TC-SRC-004: 인도 완료 물품은 검색 결과에서 제외한다.
def test_search_excludes_handed_over_items():
    register("검정 우산")
    register("빨간 우산")
    assert lost.handover("P1", True, "2026-11-26", "담당자A") == "인도 완료"

    results = lost.search_by_name("우산")

    assert len(results) == 1
    assert results[0].startswith("P2 빨간 우산")


# TC-SRC-005: 조회 결과에는 비공개 정보와 개인 전화번호를 노출하지 않는다.
def test_search_result_exposes_only_public_information():
    lost.RegisterItem("검정 우산", "기타", "2026-11-12", "학생지원팀 보관함", "학생A", "전화번호 010-1234-5678")

    result = lost.search_by_name("우산")[0]

    assert "학생A" not in result
    assert "010-1234-5678" not in result
    assert "P1" in result
    assert "검정 우산" in result
    assert "기타" in result
    assert "학생지원팀 보관함" in result


# TC-HDO-001: 주인 확인이 끝난 보관 중 물품을 인도 완료로 갱신한다.
def test_handover_marks_only_target_item_as_handed_over():
    register("검정 우산")
    register("파란 물병")
    second_before = copy.deepcopy(lost.items[1])

    assert lost.handover("P1", True, "2026-11-26", "담당자A") == "인도 완료"
    assert lost.items[0]["status"] == "인도 완료"
    assert lost.items[0]["handover_date"] == "2026-11-26"
    assert lost.items[0]["staff"] == "담당자A"
    assert lost.items[1] == second_before


# TC-HDO-002: 빈 값 또는 None 물품 번호로는 인도하지 않는다.
@pytest.mark.parametrize("item_no", ["", None])
def test_handover_rejects_blank_or_none_item_number_without_mutation(item_no):
    register()
    before = copy.deepcopy(lost.items)

    assert lost.handover(item_no, True, "2026-11-26", "담당자A") == "물품 번호를 입력하세요"
    assert lost.items == before


# TC-HDO-003: 등록되지 않은 물품 번호는 인도하지 않는다.
def test_handover_rejects_unknown_item_number_without_mutation():
    register()
    before = copy.deepcopy(lost.items)

    assert lost.handover("P999", True, "2026-11-26", "담당자A") == "등록되지 않은 물품 번호입니다"
    assert lost.items == before


# TC-HDO-004: 이미 인도 완료된 물품의 재인도를 막는다.
def test_handover_rejects_already_handed_over_item_without_overwriting_details():
    register()
    assert lost.handover("P1", True, "2026-11-20", "담당자B") == "인도 완료"
    before = copy.deepcopy(lost.items[0])

    assert lost.handover("P1", True, "2026-11-26", "담당자A") == "이미 인도된 물품입니다"
    assert lost.items[0] == before


# TC-HDO-005: 주인 확인이 True가 아니면 인도하지 않는다.
@pytest.mark.parametrize("owner_checked", [False, None])
def test_handover_requires_confirmed_owner(owner_checked):
    register()

    assert lost.handover("P1", owner_checked, "2026-11-26", "담당자A") == "주인 확인이 필요합니다"
    assert lost.items[0] == {
        "no": "P1", "name": "검정 우산", "category": "기타",
        "found_date": "2026-11-12", "location": "학생지원팀 보관함", "status": "보관 중",
    }


# TC-HDO-006: 빈 값 또는 None 인도일로는 인도하지 않는다.
@pytest.mark.parametrize("today", ["", None])
def test_handover_requires_handover_date(today):
    register()
    before = copy.deepcopy(lost.items)

    assert lost.handover("P1", True, today, "담당자A") == "인도일을 입력하세요"
    assert lost.items == before


# TC-HDO-007: 빈 값 또는 None 담당자로는 인도하지 않는다.
@pytest.mark.parametrize("staff", ["", None])
def test_handover_requires_staff_name(staff):
    register()
    before = copy.deepcopy(lost.items)

    assert lost.handover("P1", True, "2026-11-26", staff) == "담당자를 입력하세요"
    assert lost.items == before


# TC-HDO-008: 업무 규칙 밖의 상태인 물품은 인도하지 않는다.
def test_handover_rejects_unknown_status_without_mutation():
    register()
    lost.items[0]["status"] = "폐기"
    before = copy.deepcopy(lost.items)

    assert lost.handover("P1", True, "2026-11-26", "담당자A") == "알 수 없는 상태입니다"
    assert lost.items == before


# TC-CNT-001: 보관 중과 인도 완료 물품 수를 상태별로 집계한다.
def test_count_by_status_counts_each_valid_status_without_mutation():
    register("검정 우산")
    register("파란 물병")
    register("빨간 우산")
    lost.handover("P3", True, "2026-11-26", "담당자A")
    before = copy.deepcopy(lost.items)

    assert lost.count_by_status() == {"보관 중": 2, "인도 완료": 1}
    assert lost.items == before


# TC-LNG-001: 31일 보관 중인 물품은 장기 보관 목록에 포함한다.
def test_find_long_term_items_includes_item_stored_for_31_days():
    register(found_date="2026-10-26")
    before = copy.deepcopy(lost.items)

    assert lost.find_long_term_items("2026-11-26") == ["P1"]
    assert lost.items == before


# TC-LNG-002: 정확히 30일 보관한 물품은 장기 보관 목록에서 제외한다.
def test_find_long_term_items_excludes_item_stored_for_exactly_30_days():
    register(found_date="2026-10-27")
    before = copy.deepcopy(lost.items)

    assert lost.find_long_term_items("2026-11-26") == []
    assert lost.items == before


# TC-LNG-003: 29일 보관한 물품은 장기 보관 목록에서 제외한다.
def test_find_long_term_items_excludes_item_stored_for_29_days():
    register(found_date="2026-10-28")
    before = copy.deepcopy(lost.items)

    assert lost.find_long_term_items("2026-11-26") == []
    assert lost.items == before


# TC-LNG-004: 인도 완료된 물품은 오래 보관했어도 장기 보관 목록에서 제외한다.
def test_find_long_term_items_excludes_handed_over_items():
    register("검정 우산", found_date="2026-10-01")
    register("파란 물병", found_date="2026-10-20")
    lost.handover("P1", True, "2026-11-26", "담당자A")
    before = copy.deepcopy(lost.items)

    assert lost.find_long_term_items("2026-11-26") == ["P2"]
    assert lost.items == before


# TC-LNG-005: 여러 장기 보관 물품은 등록 순서대로 반환한다.
def test_find_long_term_items_returns_multiple_items_in_registration_order():
    register("검정 우산", found_date="2026-10-01")
    register("파란 물병", found_date="2026-11-01")
    register("빨간 우산", found_date="2026-10-20")
    before = copy.deepcopy(lost.items)

    assert lost.find_long_term_items("2026-11-26") == ["P1", "P3"]
    assert lost.items == before


# TC-LNG-006: 장기 보관 대상이 없으면 빈 목록을 반환한다.
def test_find_long_term_items_returns_empty_list_when_no_item_qualifies():
    register(found_date="2026-11-01")
    before = copy.deepcopy(lost.items)

    assert lost.find_long_term_items("2026-11-26") == []
    assert lost.items == before
