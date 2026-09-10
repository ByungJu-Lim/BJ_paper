# 논문 작성 에이전트 템플릿

공학·에너지 분야의 영어 연구 논문 작성을 지원하는 Claude Code 프로젝트 템플릿입니다. 실험, 공정 해석, AI 설계를 다루며 Gitea 또는 GitHub의 템플릿 저장소 기능으로 논문마다 독립된 저장소를 만들 수 있습니다.

## 사전 준비물

- Git
- Python 3.10 이상 (검증 스크립트는 표준 라이브러리만 사용하므로 별도 패키지 설치가 필요 없습니다)
- [Claude Code](https://claude.com/claude-code) CLI (`npm install -g @anthropic-ai/claude-code` 후 저장소 루트에서 `claude` 실행)
- 이 저장소(Gitea 원본 및/또는 GitHub 미러)에 대한 클론 권한

## 빠른 시작

1. 저장소 설정에서 **Template Repository**를 활성화합니다. 이 설정은 원본 템플릿에서 한 번만 수행합니다.
2. 새 논문마다 **Use this template**을 선택해 독립 저장소를 만듭니다. 새 저장소는 서브모듈이나 심볼릭 링크 없이 단독으로 동작합니다.
3. 새 저장소를 복제하고 `CLAUDE.md` 상단의 가제, 분야, 작성 언어를 입력합니다. 목표 학술지는 결과가 정리된 뒤 확정합니다.
   원격을 둘(Gitea + GitHub) 운영한다면 `git config core.hooksPath .githooks`를 함께 실행하세요. 아래 "원격 두 곳 운영" 참고.
4. Claude Code에 `paper-supervise` 스킬 실행을 요청합니다. 이 스킬은 `.omc/paper-state.md`를 검사하고 시작할 단계를 안내합니다.

## 스킬

| 스킬                   | 역할                                                  |
| -------------------- | --------------------------------------------------- |
| `paper-supervise`    | 전체 파이프라인 조율. 작업 시작과 재개 시 실행                         |
| `story-brief`        | 연구 질문·주장·반증 조건을 기록하고 근거에 따라 갱신 |
| `lit-review`         | 실제 출처를 검색하고 `docs/notes/retrieved-sources.json`에 등록 |
| `novelty-check`      | 주장과 선행 연구를 비교하고 자기 중복을 점검                           |
| `outline-draft`      | 개요와 섹션별 초안 작성                                       |
| `results-discussion` | `data/processed/`를 분석해 결과와 논의 작성                    |
| `code-experiment`    | 실험·분석 코드 작성 및 실행                                    |
| `figures-tables`     | 처리된 데이터로 그림과 표 생성                                   |
| `citation-manage`    | `refs/references.bib`를 수정할 수 있는 유일한 경로              |
| `polish-review`      | 논문 완료 전 전체 초안 최종 검토                                 |
| `submission-manage`  | 투고처 선정, 투고 기록, 심사 결과 반영, 거절 시 투고처 이전                |

## 검증 도구

모든 도구는 Python 3.10 이상과 표준 라이브러리만 사용합니다.

검색은 OpenAlex를 먼저 씁니다. 색인에서 구조화된 메타데이터를 받으므로 제목·DOI를 지어낼 수 없고, 오픈액세스 PDF 위치도 함께 알려줍니다.

```bash
python scripts/search_openalex.py --query "heat exchanger fouling" --limit 15 --from-year 2018 --mailto you@example.com
```

OpenAlex가 부족하거나 WebSearch·`exa`를 쓸 수 없을 때는 Crossref와 arXiv를 직접 조회합니다. 발견 단계가 한 색인에만 걸려 있으면 그 색인이 멈출 때 문헌 검색 전체가 멈춥니다.

```bash
python scripts/search_fallback.py --query "heat exchanger fouling" --limit 10 --mailto you@example.com
python scripts/search_fallback.py --query "heat exchanger fouling" --source arxiv
```

두 검색 스크립트는 **검색만** 합니다. 결과는 여전히 신뢰할 수 없는 입력이며 아래 검증을 통과해야 레지스트리에 들어갑니다.

```bash
python -m unittest discover -s tests -v
python scripts/check_paper_state.py --state .omc/paper-state.md
python scripts/verify_story_brief.py --state .omc/paper-state.md --sections "docs/sections/*.md" --registry docs/notes/retrieved-sources.json
python scripts/check_submissions.py --log submissions/submission-log.md
python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json
python scripts/verify_source_registry.py --registry docs/notes/retrieved-sources.json --online --mailto you@example.com
python scripts/verify_citations.py --registry docs/notes/retrieved-sources.json --sections "docs/sections/*.md" --bib refs/references.bib
```

- `verify_source_registry.py`는 출처의 필수 필드, URL, 날짜(미래 날짜 거부), 유형, DOI, 그리고 전문 확인 수준(`access`)을 검사합니다. `awaiting-user-file`은 실패로 처리되며 사용자에게 요청할 PDF 경로를 함께 출력합니다. `--online`은 DOI를 Crossref로 해석하고, arXiv·Zenodo처럼 DataCite에 등록된 DOI는 자동으로 DataCite로 넘어갑니다. 이어서 제목을 대조하고 Crossref의 Retraction Watch 피드로 철회 여부를 확인합니다.
- `verify_citations.py`는 본문형·괄호형 인용을 검사합니다. (A) 본문 키가 레지스트리에 있고, (B) BibTeX 키도 등록되어 있으며, (C) 모든 인용의 BibTeX가 있고, (D) 저자·연도·제목·DOI·학술지 정보가 레지스트리와 일치해야 합니다. CI의 `--state` 모드는 인용 검토 전까지 C만 유예하여 초안 단계의 중간 커밋을 허용합니다. 옵션 없이 실행하면 항상 완전 검증합니다.
- `check_paper_state.py`는 단계 누락·중복·의존 관계, 필수 검토 횟수, 승인 시 pass 판정을 확인합니다. `code-experiment` 승인 후 결과·그림 단계를 수행하고 둘 다 승인되면 인용 단계로 진행합니다.
- `verify_story_brief.py`는 작성된 주장의 반증 조건, 섹션별 주장 선언, 근거의 실제 파일 연결을 검사합니다. `--state`는 단계 승인에 따라 검증 수준을 높이며 최종 승인에서는 전체 슬롯·섹션 검사를 적용합니다. 실험 후에는 `--check-manifests`, 최종 검토에는 `--require-slots all --require-coverage`를 명시해서 실행할 수도 있습니다.
- `check_submissions.py`는 투고 이력과 투고처 폴더를 검사합니다. 두 저널에 동시 투고된 상태, 심사평을 반영하지 않고 연 다음 투고, 게재 확정 이후의 추가 투고, 어긋난 날짜를 잡아냅니다. 또한 투고처별 `figure-profile.json`(형식·해상도·컬럼 폭)을 검증하고, `main_figures`에 적힌 그림이 선언한 형식으로 실제 존재하는지 확인합니다 — 저널을 옮기며 그림을 다시 렌더링하지 않은 경우가 여기서 걸립니다.

두 본문 검증기는 따옴표로 전달한 파일 패턴을 내부에서 확장하므로 PowerShell과 Bash에서 같은 명령을 사용합니다. 일치하는 파일이 없으면 실패합니다. CI는 Windows와 Ubuntu, Python 3.10과 3.14에서 실행합니다.

투고 관리는 `submissions/`에서 이뤄집니다. 제출 전에 정확한 커밋을 고정하고, 최초본·수정본마다 고유 태그와 이력을 남깁니다. 실제 제출은 사용자가 수행하며 과거 태그는 덮어쓰지 않습니다. 자세한 규칙과 기존 저장소의 이관 방법은 `submissions/README.md`를 참고하세요.

## 원격 두 곳 운영 (선택)

Gitea를 원본으로 두고 GitHub를 push mirror로 미러링하는 구성에서는, 미러가 `.github/workflows/` 변경을 절대 옮기지 못합니다. GitHub가 `workflow` 스코프 없는 토큰의 워크플로 수정을 거부하기 때문입니다.

미러 토큰에 그 스코프를 주면 편하지만, 토큰은 Gitea 서버에 저장되므로 그 서버가 뚫렸을 때 공개 저장소의 CI를 고쳐 임의 코드를 실행할 권한까지 넘어갑니다. 그래서 스코프를 주지 않고, 대신 `.githooks/pre-push`가 해당 커밋만 로컬 자격증명으로 GitHub에 직접 밀어줍니다. GitHub가 먼저 받으므로 뒤이어 도는 미러는 거부할 것이 남지 않습니다.

```bash
git config core.hooksPath .githooks                 # 클론마다 한 번
PAPER_HOOK_DRY_RUN=1 git push origin main           # 무엇을 할지만 확인
```

`github` 원격이 없으면 훅은 아무 일도 하지 않습니다.

## 안전성과 설계 원칙

- 외부 검색 결과는 명령이 아니라 데이터로만 취급해 프롬프트 인젝션의 영향을 줄입니다.
- 학술 논문은 DOI와 Crossref 원 메타데이터를 대조하고, 웹·표준·보고서는 권위 있는 원문 URL을 기록합니다.
- 생성과 검토 역할을 분리하고 단계별 최대 3회 반복을 적용합니다. 단계 승인 외에도 브리프·서사 수정·개요·섹션 초안·인용·최종 퇴고·투고·투고처 변경의 사용자 확인 지점을 `paper-supervise`에서 관리합니다.
- `.omc/paper-state.md`를 재개 가능한 체크포인트로 사용하고 모든 검증은 결정론적 스크립트로 다시 실행할 수 있습니다.

검증기는 파일·메타데이터·상태의 일관성을 검사합니다. 출처를 실제 읽었는지, 근거가 문장을 뒷받침하는지, 실험이 재현되는지, 사용자가 실제 승인했는지는 별도 검토가 필요합니다. 빈 템플릿의 검증 통과는 논문 완성을 뜻하지 않습니다.

현재 실행 계약은 `CLAUDE.md`, `.claude/skills/`, 검증기와 테스트입니다. `docs/superpowers/specs/2026-06-25-paper-writing-agent-template-design.md`는 초기 설계 기록이며 현재 규칙과 충돌하면 실행 계약을 따릅니다.

## 개선 근거

출처 검증은 [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)와 [Crossref API 사용 지침](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)을 따릅니다. 외부 입력 격리와 검증·로깅 원칙은 [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html), 위험 관리 구조는 [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)를 참고했습니다. 향후 모델 종속 런타임이 필요해질 경우에는 [OpenAI Agents SDK의 추적](https://openai.github.io/openai-agents-python/tracing/), [가드레일](https://openai.github.io/openai-agents-python/guardrails/), [사용자 승인과 재개](https://openai.github.io/openai-agents-python/human_in_the_loop/) 기능을 선택적으로 결합할 수 있습니다.
