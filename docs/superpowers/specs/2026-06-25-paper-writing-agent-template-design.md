# 논문 작성 에이전트 템플릿 설계

> 초기 설계 기록입니다. 현재 단계·승인·검증 계약은 `CLAUDE.md`, `.claude/skills/`, `scripts/`와 테스트를 따릅니다. 2026-09-07 검토에서 story-brief, 코드 선행 실행, 투고 버전 이력과 강화된 검증을 반영했습니다.

- Status: Approved (design), pending implementation plan
- Date: 2026-06-25

## 1. 목적

공학/에너지 분야(실험, 공정해석, AI 설계 포함) 영어 논문 작성을 돕는 Claude Code 프로젝트 템플릿을 만든다. 이 템플릿은 Gitea에 **Template Repository**로 저장하고, 새 논문을 시작할 때마다 "Use this template"으로 독립된 저장소를 생성해 재사용한다.

작성 방식은 Markdown 우선(초안) → 후속 변환(Pandoc 등으로 LaTeX/Word/PDF화)이며, 출력 포맷 자체는 템플릿의 핵심 관심사가 아니다.

## 2. 범위와 비범위

**범위(이 템플릿이 다루는 것):**
- 문헌조사/정리, novelty 도출, 자기중복(redundancy) 검토
- 아웃라인 설계, 섹션별 초안 작성
- 실험결과 분석, discussion 작성
- 실험/분석 코드 작성, 표·그림 생성
- 인용/참조문헌 관리 (환각 방지 포함)
- 퇴고/문체 교정
- 전체 진행을 조율하는 "논문 감독"

**비범위:**
- 특정 저널/컨퍼런스 LaTeX 클래스 자동 적용 (필요 시 별도 후속 작업)
- 실제 실험 장비 제어, 데이터 수집 자체
- 공동저자 간 실시간 협업 도구

## 3. 아키텍처 결정: 하이브리드 (스킬 + 단일 오케스트레이터)

전역 CLAUDE.md에 이미 구성된 oh-my-claudecode(OMC)의 범용 에이전트를 재사용한다:
- `scientist` → 문헌조사, 실험결과 분석, novelty 비교
- `writer` → 초안/섹션 작성, discussion 서술
- `executor` → 실험/분석 코드, 표·그림 생성 스크립트
- `critic` / `verifier` → 리뷰, 인용 검증, 일관성 점검

새로 정의하는 것은 **`.claude/skills/` 아래의 논문 전용 스킬들**과, 전체 진행을 조율하는 **단일 오케스트레이터 스킬 `paper-supervise`** 뿐이다. 전용 에이전트를 따로 만들지 않아 OMC와의 역할 중복/유지보수 부담을 피한다.

이 결정은 다음 조사 결과로 보강되었다 (Sources 참고):
- Agent Laboratory의 역할 분담(생성 vs 검증 분리) 패턴을 critic/verifier 분리로 채택
- 완전자율보다 체크포인트형(co-pilot) 운용이 연구 무결성에 더 안전하다는 결론 → 사용자 승인 게이트 채택

## 4. 디렉토리 구조

```
paper-project/
├── CLAUDE.md                       # 논문 메타데이터(분야/언어/타겟 저널) + 워크플로 안내
├── .claude/
│   └── skills/
│       ├── paper-supervise/        # 오케스트레이터
│       ├── lit-review/
│       ├── novelty-check/
│       ├── outline-draft/
│       ├── results-discussion/
│       ├── code-experiment/
│       ├── figures-tables/
│       ├── citation-manage/
│       └── polish-review/
├── .omc/
│   └── paper-state.md              # 진행상황 추적 (스키마는 6절)
├── docs/
│   ├── outline.md
│   ├── sections/
│   │   ├── 01-introduction.md
│   │   ├── 02-related-work.md
│   │   ├── 03-methods.md
│   │   ├── 04-results.md
│   │   ├── 05-discussion.md
│   │   └── 06-conclusion.md
│   └── notes/
│       ├── retrieved-sources.json  # 실제 검색된 출처 레지스트리 (인용 환각 방지용)
│       └── novelty-matrix.md       # 주장 vs 선행연구 vs 차이점
├── refs/
│   └── references.bib
├── code/
├── data/
│   ├── raw/
│   └── processed/
└── figures/
```

## 5. 스킬별 입출력 계약

| 스킬 | 입력 | 호출 에이전트 | 출력 |
|---|---|---|---|
| `lit-review` | 연구 주제/키워드 | scientist (WebSearch 기반 실제 검색) | `docs/notes/*.md` + `retrieved-sources.json` 등록 |
| `novelty-check` | outline/draft + retrieved-sources | scientist → critic | `docs/notes/novelty-matrix.md`(분야 대비 novelty), 자기중복도 체크(본인 선행 논문과의 중복률) |
| `outline-draft` | novelty-matrix | writer → critic | `docs/outline.md`, `docs/sections/*.md` |
| `results-discussion` | `data/processed/*` | scientist → writer → critic | `docs/sections/04-results.md`, `05-discussion.md` |
| `code-experiment` | 실험/분석 요구사항 | executor | `code/*`, `data/processed/*` |
| `figures-tables` | `data/processed/*` | executor → critic | `figures/*.png`, 표 마크다운 |
| `citation-manage` | 섹션 내 인용 주장 | verifier (RAG 그라운딩, retrieved-sources만 허용) | `refs/references.bib`, `rejected-citations` 로그 |
| `polish-review` | 전체 draft | critic (5축 루브릭, 7절 참고) | 최종 검토 리포트 |
| `paper-supervise` | 전체 | 오케스트레이터, `.omc/paper-state.md` 읽고씀 | 6절의 루프 실행 + 사용자 게이트 |

## 6. 진행상황 추적: `.omc/paper-state.md`

스테이지별로 다음 필드를 가진 섹션을 가진다.

```markdown
## Stage: <stage-id>
status: not-started | in-progress | awaiting-review | awaiting-user | approved | escalated
round: <n>/3
last-critic-verdict: pass | revise
last-critic-issues:
  - "..."
```

`citation-manage` 단계는 추가로 `verified-sources`(검증된 출처 수)와 `rejected-citations`(반려된 인용 + 반려 이유)를 기록한다.

## 7. 감독 루프 로직 (스테이지마다 동일 적용)

1. 담당 에이전트(writer/scientist/executor)가 산출물 생성
2. critic/verifier가 5축으로 평가: **novelty/significance, 기술적 타당성, 명료성, 선행연구 커버리지, 구체적 수정 제안** (AgentReview 리뷰 구조 차용)
3. 평가가 `pass`면 → `status: awaiting-user`로 멈추고 사용자 승인 대기
4. 평가가 `revise`면 → 이슈를 반영해 라운드 +1, 재생성
5. 라운드가 3을 초과해도 `revise`면 → `status: escalated`로 멈추고 남은 이슈를 사용자에게 보고 (자동 통과나 무한반복 금지)
6. 사용자가 게이트에서 반려하면 다시 2단계로

**고정 사용자 승인 게이트 4곳** (critic 통과와 무관하게 항상 사용자 확인을 거침): 아웃라인 완료, 각 섹션 초안 완료, 인용 확정 전, 최종 퇴고 전.

## 8. 인용 환각 방지 (citation-manage 핵심 규칙)

연구에 따르면 LLM은 모델 기억만으로 인용을 생성할 경우 최대 95%까지 존재하지 않는 참고문헌을 만들어낸다. 이를 막기 위해:

- 모든 인용은 `lit-review` 단계에서 실제 WebSearch/검색으로 확인된 출처만 `docs/notes/retrieved-sources.json`에 등록
- `citation-manage`는 섹션에서 사용된 모든 인용 주장을 이 레지스트리와 교차검증
- 레지스트리에 없는 인용은 `refs/references.bib`에 추가하지 않고 `rejected-citations` 로그에 기록, 사용자에게 보고
- 본문에서 직접 모델이 BibTeX 항목을 "만들어내는" 경로는 허용하지 않음

## 9. novelty-check 3단계 파이프라인

자동 novelty 평가 연구의 구조를 차용:
1. 자기 논문의 주장/contribution 추출
2. 관련 문헌 검색 및 랭킹 (retrieved-sources 활용)
3. "주장 vs 가장 가까운 선행연구 vs 차이점" 구조화 비교 → `novelty-matrix.md`

별도로 자기중복(redundancy) 체크: 본인의 기존 발표/논문과 표현·기여도가 얼마나 겹치는지 비율로 보고 (중복게재 리스크 관리).

## 10. Gitea 배포 방식

이 템플릿 저장소를 Gitea에서 "Template Repository"로 설정한다. 새 논문을 시작할 때 "Use this template"으로 독립된 새 저장소를 생성하며, 템플릿과 실제 논문 저장소 사이에 submodule/symlink 등 런타임 의존성은 두지 않는다 (완전 독립).

## 11. 향후 구현 범위 (다음 단계인 구현 계획에서 다룰 것)

- `CLAUDE.md` 본문 작성 (메타데이터 플레이스홀더 + 워크플로 안내)
- 각 스킬의 `SKILL.md` 작성
- `paper-supervise` 오케스트레이터 스킬의 상세 로직
- `.omc/paper-state.md` 초기 템플릿 파일
- 샘플 `retrieved-sources.json`, `novelty-matrix.md` 템플릿
- Gitea 저장소 생성 및 Template 플래그 설정 (사용자 확인 후 수행)

## Sources

- [Agent Laboratory: Using LLM Agents as Research Assistants](https://arxiv.org/pdf/2501.04227)
- [AgentRxiv: Towards Collaborative Autonomous Research](https://arxiv.org/pdf/2503.18102)
- [BibTeX Citation Hallucinations in Scientific Publishing Agents: Evaluation and Mitigation](https://arxiv.org/pdf/2604.03159)
- [Detecting and Correcting Reference Hallucinations in Commercial LLMs and Deep Research Agents](https://arxiv.org/html/2604.03173v1)
- [Automated Novelty Evaluation of Academic Paper](https://arxiv.org/pdf/2507.11330)
- [AgentReview: Exploring Peer Review Dynamics with LLM Agents](https://arxiv.org/html/2406.12708v2)
