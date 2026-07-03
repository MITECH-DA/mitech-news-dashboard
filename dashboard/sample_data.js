// trend_report.py가 생성하는 CSV와 동일한 구조의 샘플 데이터입니다.
// "샘플 데이터로 미리보기" 버튼을 누르면 이 데이터로 대시보드를 렌더링합니다.
const SAMPLE_CSV = `published_date,source,title,url,image_url,category,companies,products,technologies,indications,competitor_flag,sentiment,summary
2026-06-15,MassDevice,Boston Scientific wins FDA nod for biodegradable coronary stent,https://example.com/1,,신제품출시,Boston Scientific,Synergy Bio,생분해성 스텐트,관상동맥질환,True,긍정,Boston Scientific이 생분해성 관상동맥 스텐트에 대해 FDA 승인을 받았다.
2026-06-15,MedTech Dive,Medtronic reports steady Q2 cardiovascular device sales,https://example.com/2,,실적/경영,Medtronic,,약물방출 스텐트,관상동맥질환,True,중립,Medtronic의 2분기 심혈관 기기 매출이 안정적으로 유지됐다.
2026-06-16,Naver News,엠아이텍 말초혈관 스텐트 수출 확대,https://example.com/3,,실적/경영,M.I.Tech,,말초혈관 스텐트,말초혈관질환,False,긍정,엠아이텍이 동남아 시장으로 말초혈관 스텐트 수출을 확대했다.
2026-06-17,MDDI,Abbott announces clinical trial results for AI-guided imaging catheter,https://example.com/4,,임상시험,Abbott,Xperience AI,AI 영상 가이드,관상동맥질환,True,긍정,Abbott이 AI 기반 영상 가이드 카테터의 임상 결과를 발표했다.
2026-06-18,MassDevice,Terumo recalls certain peripheral catheter batches,https://example.com/5,,리콜/이슈,Terumo,,카테터,말초혈관질환,True,부정,Terumo가 제조 결함으로 일부 말초 카테터 배치를 리콜했다.
2026-06-19,Naver News,식약처 자가팽창 스텐트 신규 허가 3건 승인,https://example.com/6,,규제/인허가,,,자가팽창 스텐트,관상동맥질환,False,중립,식약처가 자가팽창 스텐트 관련 신규 허가 3건을 승인했다.
2026-06-20,MedTech Dive,Boston Scientific to acquire AI diagnostics startup,https://example.com/7,,M&A/투자,Boston Scientific,,AI 진단,,True,긍정,Boston Scientific이 AI 진단 스타트업 인수를 발표했다.
2026-06-21,MassDevice,Cook Medical expands biodegradable stent research partnership,https://example.com/8,,R&D/기술,Cook Medical,,생분해성 스텐트,관상동맥질환,True,긍정,Cook Medical이 생분해성 스텐트 연구 파트너십을 확대했다.
2026-06-22,MDDI,Medtronic launches next-gen drug-eluting stent in Europe,https://example.com/9,,신제품출시,Medtronic,Resolute Onyx X,약물방출 스텐트,관상동맥질환,True,긍정,Medtronic이 유럽에 차세대 약물방출 스텐트를 출시했다.
2026-06-22,Naver News,엠아이텍 AI 품질검사 시스템 도입,https://example.com/10,,R&D/기술,M.I.Tech,,AI 품질검사,,False,긍정,엠아이텍이 생산 공정에 AI 품질검사 시스템을 도입했다.
2026-06-23,MedTech Dive,Abbott peripheral stent faces new competition in Asia,https://example.com/11,,실적/경영,Abbott,,말초혈관 스텐트,말초혈관질환,True,중립,Abbott의 말초혈관 스텐트가 아시아 시장에서 경쟁 심화에 직면했다.
2026-06-24,MassDevice,Terumo reports positive trial data for self-expanding stent,https://example.com/12,,임상시험,Terumo,,자가팽창 스텐트,말초혈관질환,True,긍정,Terumo가 자가팽창 스텐트의 긍정적인 임상 데이터를 발표했다.
2026-06-25,MDDI,FDA flags safety concern with certain drug-eluting stents,https://example.com/13,,리콜/이슈,Boston Scientific,,약물방출 스텐트,관상동맥질환,True,부정,FDA가 일부 약물방출 스텐트에 대한 안전성 우려를 제기했다.
2026-06-26,Naver News,식약처 스텐트 품목허가 심사기간 단축 발표,https://example.com/14,,규제/인허가,,,,,False,긍정,식약처가 스텐트 품목허가 심사기간을 단축한다고 발표했다.
2026-06-27,MedTech Dive,Microport expands biodegradable stent manufacturing capacity,https://example.com/15,,R&D/기술,Microport,,생분해성 스텐트,관상동맥질환,True,긍정,Microport가 생분해성 스텐트 생산 능력을 확대했다.
2026-06-28,MassDevice,Boston Scientific Q2 revenue beats estimates on stent demand,https://example.com/16,,실적/경영,Boston Scientific,,약물방출 스텐트,관상동맥질환,True,긍정,Boston Scientific의 2분기 매출이 스텐트 수요에 힘입어 예상치를 상회했다.
2026-06-29,Naver News,엠아이텍 심혈관 스텐트 국내 점유율 확대,https://example.com/17,,실적/경영,M.I.Tech,,약물방출 스텐트,관상동맥질환,False,긍정,엠아이텍이 국내 심혈관 스텐트 시장 점유율을 확대했다.
2026-06-30,MDDI,Medtronic AI imaging platform receives CE mark,https://example.com/18,,규제/인허가,Medtronic,,AI 영상 가이드,,True,긍정,Medtronic의 AI 영상 플랫폼이 CE 인증을 획득했다.
2026-07-01,MassDevice,Cook Medical catheter recall widens to additional lots,https://example.com/19,,리콜/이슈,Cook Medical,,카테터,말초혈관질환,True,부정,Cook Medical의 카테터 리콜이 추가 로트로 확대됐다.
2026-07-01,MedTech Dive,Abbott announces new coronary stent trial enrollment complete,https://example.com/20,,임상시험,Abbott,,약물방출 스텐트,관상동맥질환,True,중립,Abbott이 관상동맥 스텐트 임상시험 등록을 완료했다고 발표했다.
2026-07-02,Naver News,국내 의료기기 AI 진단 스타트업 투자 유치 잇따라,https://example.com/21,,M&A/투자,,,AI 진단,,False,긍정,국내 의료기기 AI 진단 스타트업들이 잇따라 투자를 유치했다.
2026-07-02,MassDevice,Terumo self-expanding stent gains FDA breakthrough designation,https://example.com/22,,규제/인허가,Terumo,,자가팽창 스텐트,말초혈관질환,True,긍정,Terumo의 자가팽창 스텐트가 FDA 혁신의료기기 지정을 받았다.
2026-07-03,MDDI,Boston Scientific biodegradable stent shows 5-year durability,https://example.com/23,,R&D/기술,Boston Scientific,,생분해성 스텐트,관상동맥질환,True,긍정,Boston Scientific의 생분해성 스텐트가 5년 내구성 데이터를 공개했다.
2026-07-03,Naver News,엠아이텍 신규 카테터 라인업 개발 착수,https://example.com/24,,R&D/기술,M.I.Tech,,카테터,말초혈관질환,False,긍정,엠아이텍이 신규 카테터 라인업 개발에 착수했다.
`;
