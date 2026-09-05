# 논문 작성 에이전트 템플릿

공학·에너지 분야의 영어 연구 논문 작성을 지원하는 Claude Code 프로젝트 템플릿입니다. 실험, 공정 해석, AI 설계를 다루며 Gitea 또는 GitHub의 템플릿 저장소 기능으로 논문마다 독립된 저장소를 만들 수 있습니다.

## 빠른 시작

1. 저장소 설정에서 **Template Repository**를 활성화합니다. 이 설정은 원본 템플릿에서 한 번만 수행합니다.
2. 새 논문마다 **Use this template**을 선택해 독립 저장소를 만듭니다. 새 저장소는 서브모듈이나 심볼릭 링크 없이 단독으로 동작합니다.
3. 새 저장소를 복제하고 `CLAUDE.md` 상단의 가제, 목표 학술지/학회, 분야, 작성 언어를 입력합니다.
4. Claude Code에 `paper-supervise` 스킬 실행을 요청합니다. 이 스킬은 `.omc/paper-state.md`를 검사하고 시작할 단계를 안내합니다.

## 스킬

| 스킬 | 역할 |
|---|---|
| `paper-supervise` | 전체 파이프라인 조율. 작업 시작과 재개 시 실행 |
| `lit-review` | 실제 출처를 검색하고 `docs/notes/retrieved-sources.json`에 등록 |
| `novelty-check` | 주장과 선행 연구를 비교하고 자기 중복을 점검 |
| `outline-draft` | 개요와 섹션별 초안 작성 |
| `results-discussion` | `data/processed/`를 분석해 결과와 논의 작성 |
| `code-experiment` | 실험·분석 코드 작성 및 실행 |
| `figures-tables` | 처리된 데이터로 그림과 표 생성 |
| `citation-manage` | `refs/references.bib`를 수정할 수 있는 유일한 경로 |
| `polish-review` | 논문 완료 전 전체 초안 최종 검토 |

## 검증 도구

모든 도구는 Python 3.10 이상과 표준 라이브러리만 사용합니다.

```bash
python -m unittest discover -s tests -v
python scripts/check_paper_state.py --state .omc/paper-state.md
python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json
python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json --online --mailto you@example.com
python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections docs/sections/*.md --bib refs/references.bib
```

- `verify_source_registry.py`는 출처의 필수 필드, URL, 날짜(미래 날짜 거부), 유형, DOI를 검사합니다. `--online`은 DOI를 Crossref로 해석하고, arXiv·Zenodo처럼 DataCite에 등록된 DOI는 자동으로 DataCite로 넘어갑니다. 이어서 제목을 대조하고 Crossref의 Retraction Watch 피드로 철회 여부를 확인합니다.
- `verify_citations.py`는 세 가지 불변식을 강제합니다. (A) 본문 인용 키가 모두 레지스트리에 있을 것, (B) BibTeX 항목이 모두 레지스트리에 있을 것, (C) 본문 인용 키가 모두 BibTeX에 있을 것. B가 없으면 `.bib`에 직접 써넣은 조작 항목을 아무도 잡지 못합니다.
- `check_paper_state.py`는 단계 누락·중복·순서, 상태값, 검토 횟수 제한을 확인합니다.

## 안전성과 설계 원칙

- 외부 검색 결과는 명령이 아니라 데이터로만 취급해 프롬프트 인젝션의 영향을 줄입니다.
- 학술 논문은 DOI와 Crossref 원 메타데이터를 대조하고, 웹·표준·보고서는 권위 있는 원문 URL을 기록합니다.
- 생성과 검토 역할을 분리하고, 단계별 최대 3회 반복과 네 개의 사용자 승인 게이트를 유지합니다.
- `.omc/paper-state.md`를 재개 가능한 체크포인트로 사용하고 모든 검증은 결정론적 스크립트로 다시 실행할 수 있습니다.

상세 설계는 `docs/superpowers/specs/2026-06-25-paper-writing-agent-template-design.md`를 참고하세요.

## 개선 근거

출처 검증은 [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)와 [Crossref API 사용 지침](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)을 따릅니다. 외부 입력 격리와 검증·로깅 원칙은 [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html), 위험 관리 구조는 [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)를 참고했습니다. 향후 모델 종속 런타임이 필요해질 경우에는 [OpenAI Agents SDK의 추적](https://openai.github.io/openai-agents-python/tracing/), [가드레일](https://openai.github.io/openai-agents-python/guardrails/), [사용자 승인과 재개](https://openai.github.io/openai-agents-python/human_in_the_loop/) 기능을 선택적으로 결합할 수 있습니다.
