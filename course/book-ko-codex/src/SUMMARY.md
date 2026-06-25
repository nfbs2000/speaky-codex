# 목차

[서문](./preface.md)

---

# 제1부: Harness Runtime Anatomy

- [1장: 저장소 지형도 — Codex를 어떤 층으로 읽어야 하는가](./part1/ch01.md)
- [2장: 스레드와 세션 — 런타임은 어디서 시작되는가](./part1/ch02.md)
- [3장: 턴 루프 — Codex 하니스는 어떻게 한 턴을 계속 이어 가는가](./part1/ch03.md)
- [4장: 도구 표면과 라우팅 — 모델의 손은 어떻게 조직되는가](./part1/ch04.md)
- [5장: 승인·샌드박스·병렬 실행 — 정책 하니스는 어디서 성립되는가](./part1/ch05.md)
- [6장: 이벤트 스트리밍과 app-server — 하니스 계약은 어떤 이벤트로 드러나는가](./part1/ch06.md)

---

# 제2부: Control Plane as Micro Harness

- [7장: AGENTS.md — 사용자 지침은 어떻게 우선권을 얻는가](./part2/ch07.md)
- [8장: Skills — 재사용 가능한 micro harness는 어떻게 주입되는가](./part2/ch08.md)
- [9장: 초기 컨텍스트 — 하니스 입력층은 어떻게 조립되는가](./part2/ch09.md)

---

# 제3부: Memory for Long-Running Harness

- [10장: SessionState와 TurnState — 상태는 왜 둘로 나뉘는가](./part3/ch10.md)
- [11장: 히스토리 관리자와 토큰 추정 — 기억은 어떻게 계산되는가](./part3/ch11.md)
- [12장: Compaction과 Rollback — 긴 대화는 어떻게 접고 되돌리는가](./part3/ch12.md)

---

# 제4부: Policy Harness & Extensibility

- [13장: 샌드박스와 승인 정책 — 안전성은 어떤 계층으로 서는가](./part4/ch13.md)
- [14장: Hooks 시스템 — 사용자는 어디서 런타임에 개입할 수 있는가](./part4/ch14.md)
- [15장: MCP 연결 관리자 — 외부 앱과 도구는 어떻게 붙는가](./part4/ch15.md)

---

# 제5부: Subagents & Surfaces

- [16장: 리뷰 서브에이전트 — Codex는 어떻게 축소된 하니스 복제본을 만들어 검토를 외주화하는가](./part5/ch16.md)
- [17장: 모델 카탈로그와 새로고침 — 모델 선택은 왜 하니스 자원 관리인가](./part5/ch17.md)
- [18장: app-server, TUI, CLI — 같은 하니스가 어떻게 다른 표면으로 드러나는가](./part5/ch18.md)

---

# 제6부: Harness Builder Lessons

- [19장: Codex가 보여 주는 하니스 엔지니어링 원칙 — 무엇을 가져가고 무엇을 버릴까](./part6/ch19.md)

---

# 제7부: Long-Running Goal Harness

- [20장: /goal 강좌 로드맵 — 장시간 목표 루프를 어떻게 읽을 것인가](./part7/ch20.md)
- [21장: TUI 표면 — /goal 입력은 어떻게 앱 이벤트가 되는가](./part7/ch21.md)
- [22장: app-server와 저장 모델 — goal은 어떤 API와 row로 고정되는가](./part7/ch22.md)
- [23장: core goal runtime — active goal은 어떻게 다음 턴의 원인이 되는가](./part7/ch23.md)
- [24장: 모델 도구와 안전장치 — 모델은 goal을 어디까지 조작할 수 있는가](./part7/ch24.md)
- [25장: 내 하니스에 옮기기 — 장시간 목표 루프 구현 순서](./part7/ch25.md)

---

# 제8부: Desktop SDK Runtime Evidence Harness

- [26장: Desktop Runtime Evidence 하니스 — Electron 앱은 실제 Codex를 어디서 실행하는가](./part8/ch26.md)
- [27장: 개발 실행 체인 — bridge, Vite, Electron은 어떤 순서로 뜨는가](./part8/ch27.md)
- [28장: TypeScript SDK 실행 어댑터 — runStreamed()는 어떻게 실제 Codex CLI가 되는가](./part8/ch28.md)
- [29장: Renderer와 bridge protocol — React UI는 SDK를 직접 부르지 않는다](./part8/ch29.md)
- [30장: chat.run에서 runStreamed()까지 — bridge server의 한 턴 실행 루프](./part8/ch30.md)
- [31장: Runtime Evidence artifact — raw, normalized, OTel, Trajectory는 어떻게 화면이 되는가](./part8/ch31.md)

---

# 제9부: Course Evidence Implementation

- [32장: Course Evidence 로드맵 — 강좌 개념은 어떻게 실제 런타임 증거가 되는가](./part9/ch32.md)
- [33장: Rust OTel 타입 — CourseEvidenceEvent는 어떤 계약인가](./part9/ch33.md)
- [34장: core decision point 계측 — Course Evidence는 어디에 꽂혀 있는가](./part9/ch34.md)
- [35장: OTel export 검증 — codex.course_evidence는 log와 trace에 실제로 남는가](./part9/ch35.md)
- [36장: Desktop normalizer — codex.course_evidence는 어떻게 course.evidence가 되는가](./part9/ch36.md)
- [37장: Course Evidence UI와 다음 확장 — Runtime Evidence에서 무엇을 보고 무엇을 더 붙일 것인가](./part9/ch37.md)

---

# 부록

- [부록 A: 주요 파일 인덱스 — 무엇을 어디서 찾을 것인가](./appendix/a-file-index.md)
- [부록 B: 근거 사용 규칙 — 무엇을 확인이라 부르고 무엇을 추론이라 부를 것인가](./appendix/b-evidence-rules.md)
