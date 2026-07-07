// ============================================================
// 오늘의 카드뉴스 매니페스트
// 매일 이 배열만 통째로 교체하면 대시보드 상단 "01. 오늘의 카드뉴스"에 반영됩니다.
//
// 사용법:
//   1. 오늘 만든 카드뉴스 이미지(1080x1350, 4:5)를 dashboard/daily_cards/ 폴더에 넣는다.
//   2. 아래 DAILY_CARDS 배열을 오늘자 이미지+원문 URL 목록으로 통째로 교체한다.
//      (어제 파일은 남겨두든 지우든 상관없음 — 배열에 없으면 화면에 안 나옴)
//   3. index.html을 새로고침하면 바로 반영됨 (서버/빌드 불필요)
//
// 필드 설명:
//   image : dashboard/daily_cards/ 폴더 기준 상대경로
//   url   : 클릭 시 이동할 원문 기사 링크
//   title : (선택) 마우스 오버 시 툴팁 + 이미지 alt 텍스트. 비워둬도 동작함.
// ============================================================

const DAILY_CARDS = [
  {
    image: 'daily_cards/260707_Slide_1.png',
    url: 'https://buly.kr/BTRwf51',
    title: '테르모 해외서 흉부 스텐트 그라프트 자진회수',
  },
  {
    image: 'daily_cards/260707_Slide_2.png',
    url: 'https://buly.kr/YgxqVE',
    title: '엔벤트릭, 혈전제거기기 시장 진입 채비…후속 제품 개발 병행',
  },
  {
    image: 'daily_cards/260707_Slide_3.png',
    url: 'https://buly.kr/H6kC3Bx',
    title: '미래컴퍼니 수술로봇 레보아이 산업부 혁신제품 지정',
  },
  {
    image: 'daily_cards/260707_Slide_4.png',
    url: 'https://buly.kr/1GLzllr',
    title: '좌심방 시장서 또 맞붙은 메드트로닉-에드워즈 …3파전 돌입',
  },
  {
    image: 'daily_cards/260707_Slide_5.png',
    url: 'https://buly.kr/FAfrGDv',
    title: '헬스케어 기업공개 활발…의료기기·신약 성과 기대감',
  },
  {
    image: 'daily_cards/260707_Slide_6.png',
    url: 'https://buly.kr/EdvaJmL',
    title: '바이오 오픈이노베이션 확산...민간·공공 협력 구축 속도',
  },
  {
    image: 'daily_cards/260707_Slide_7.png',
    url: 'https://buly.kr/9MSqtJ4',
    title: '대구시 AI 기반 인체 이식용 섬유 의료기기 국산화 시동',
  },
  {
    image: 'daily_cards/260707_Slide_8.png',
    url: 'https://buly.kr/ET0pKy3',
    title: "글로벌 빅파마와 협력…9월 '오픈이노베이션 위크' 참가사 모집",
  },
  {
    image: 'daily_cards/260707_Slide_9.png',
    url: 'https://buly.kr/9iIMqwX',
    title: '병원·제약사와 의료AI의 만남…디산협 매칭데이 모집 연장',
  },
  {
    image: 'daily_cards/260707_Slide_10.png',
    url: 'https://buly.kr/4FusReh',
    title: '10여개국 의사 제주대병원 찾았다… 다빈치5 로봇수술 벤치마킹',
  },
];
