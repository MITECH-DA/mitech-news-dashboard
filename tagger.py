# -*- coding: utf-8 -*-
"""
LLM 태깅 모듈
- Claude API를 호출해서 기사 본문에서 회사명/제품명/기술/적응증/카테고리/감성을 JSON으로 추출
- 규칙 기반 NER보다 정확도가 높고 유지보수가 쉬움 (프롬프트만 수정하면 됨)
"""
import json
import logging
import time

import anthropic

import config

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Anthropic 클라이언트를 lazy하게 생성 (API 키 없으면 명시적으로 에러)."""
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일에 추가해주세요."
            )
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = f"""당신은 의료기기 산업 뉴스를 구조화하는 분석 보조자입니다.
주어진 기사의 제목과 본문을 분석해서 아래 JSON 스키마에 맞춰 **오직 JSON만** 출력하세요.
설명, 마크다운 코드블록(```), 추가 텍스트를 절대 포함하지 마세요.

스키마:
{{
  "category": "다음 중 하나: {', '.join(config.CATEGORIES)}",
  "companies": ["기사에 언급된 회사명 목록 (원문 표기 그대로)"],
  "products": ["기사에 언급된 제품명/브랜드명 목록"],
  "technologies": ["기사에 언급된 핵심 기술 키워드 목록 (예: 생분해성 스텐트, AI 진단, 약물방출 등)"],
  "indications": ["기사에 언급된 질환/적응증 목록 (예: 관상동맥질환, 말초혈관질환)"],
  "sentiment": "긍정 | 부정 | 중립 (해당 기사가 다루는 기업/기술에 대한 논조)",
  "summary": "한국어로 1~2문장, 핵심 내용 요약"
}}

주의사항:
- 언급이 없는 필드는 빈 배열 [] 또는 null로 두세요. 추측해서 채우지 마세요.
- category는 반드시 제시된 목록 중 하나여야 합니다.
- companies/products/technologies/indications는 기사에 실제로 등장한 표현만 사용하세요.
"""


def tag_article(title, text, max_retries=3):
    """단일 기사를 LLM으로 태깅. 실패 시 최대 max_retries회 재시도.

    Returns:
        dict (스키마와 동일한 키) 또는 실패 시 None
    """
    client = get_client()
    user_content = f"제목: {title}\n\n본문:\n{text[:4000]}"  # 토큰 절약을 위해 본문 길이 제한

    for attempt in range(1, max_retries + 1):
        try:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw_text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

            # 혹시 모델이 코드블록으로 감싸는 경우 대비한 방어 코드
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

            result = json.loads(raw_text)
            result = _postprocess(result)
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"[재시도 {attempt}/{max_retries}] JSON 파싱 실패: {e}")
        except anthropic.APIError as e:
            logger.warning(f"[재시도 {attempt}/{max_retries}] Claude API 오류: {e}")
        except Exception as e:
            logger.error(f"태깅 중 예상치 못한 오류: {e}")
            break

        time.sleep(1.5 * attempt)  # 지수적 백오프

    logger.error(f"태깅 최종 실패: {title[:50]}")
    return None


def _postprocess(result):
    """LLM 출력 후처리: 카테고리 검증, 경쟁사 플래그 부착."""
    if result.get("category") not in config.CATEGORIES:
        result["category"] = "기타"

    for field in ("companies", "products", "technologies", "indications"):
        if not isinstance(result.get(field), list):
            result[field] = []

    # 경쟁사 키워드 목록과 매칭되면 competitor_flag = True
    companies_text = " ".join(result.get("companies", [])).lower()
    result["competitor_flag"] = any(
        comp.lower() in companies_text for comp in config.COMPETITOR_KEYWORDS
    )

    return result


def tag_batch(articles):
    """여러 기사를 순차 태깅. (article_id, tag_result) 튜플 리스트 반환.
    태깅 실패한 기사는 결과에서 제외됨 (다음 실행 시 재시도됨).
    """
    results = []
    for article in articles:
        logger.info(f"태깅 중: {article['title'][:60]}")
        tag_result = tag_article(article["title"], article["raw_text"])
        if tag_result:
            results.append((article["id"], tag_result))
        time.sleep(0.3)  # rate limit 완화
    return results
