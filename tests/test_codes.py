from app import codes


def test_success_codes_have_zero_status_suffix():
    assert codes.CODE_AI_SUCCESS == 500000
    assert codes.CODE_AI_EXTRACT_SUCCESS == 500100
    assert codes.CODE_AI_VERIFY_SUCCESS == 500200
    assert codes.CODE_AI_EXTRACT_IDS_SUCCESS == 500300
    assert codes.CODE_AI_HEALTH_SUCCESS == 500900


def test_validation_codes_use_40_suffix():
    assert codes.CODE_AI_VALIDATION == 500040
    assert codes.CODE_AI_VERIFY_INVALID_INPUT == 500241


def test_internal_codes_use_50_suffix():
    assert codes.CODE_AI_INTERNAL == 500050


def test_failure_codes_use_correct_status_suffix():
    assert codes.CODE_AI_EXTRACT_OCR_FAILED == 500140
    assert codes.CODE_AI_VERIFY_OCR_FAILED == 500240
    assert codes.CODE_AI_EXTRACT_IDS_OCR_FAILED == 500340
    assert codes.CODE_AI_EXTRACT_IDS_NO_MATCHES == 500341
    assert codes.CODE_AI_HEALTH_NOT_READY == 500950


def test_no_llm_response_codes():
    from app import codes
    assert not hasattr(codes, "CODE_AI_EXTRACT_LLM_FAILED")
    assert not hasattr(codes, "CODE_AI_LLM_TIMEOUT")
    assert not hasattr(codes, "CODE_AI_VERIFY_LLM_FAILED")


def test_all_codes_are_six_digit_integers():
    code_values = [
        v for k, v in vars(codes).items()
        if k.startswith("CODE_") and isinstance(v, int)
    ]
    assert len(code_values) > 0
    for code in code_values:
        assert 100000 <= code <= 999999
