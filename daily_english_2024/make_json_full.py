import json
import re
import pdfplumber
import os

def extract_text_from_pdf(pdf_path):
    """PDF 파일에서 텍스트를 추출합니다."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        print(f"총 {len(pdf.pages)} 페이지 추출 중...")
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(pdf.pages)} 페이지 처리 완료")
    print("PDF 텍스트 추출 완료!")
    return text

def extract_day_section(text, day_number):
    """특정 DAY의 전체 섹션을 추출합니다."""
    lines = text.split('\n')
    
    # DAY 섹션 찾기
    start_idx = None
    day_number_idx = None
    end_idx = len(lines)
    
    for i, line in enumerate(lines):
        # DAY 번호 찾기 (예: "005", "006" 등)
        if line.strip() == f"{day_number:03d}":
            day_number_idx = i
            # 이전 2-3줄이 제목과 카테고리일 가능성이 높음
            # DAY 텍스트 줄 찾기
            for j in range(max(0, i-4), i):
                if lines[j].strip() == "DAY":
                    start_idx = j + 1  # DAY 다음 줄부터 시작
                    break
            
            if start_idx is None and i > 0:
                start_idx = i - 2  # 기본적으로 2줄 전부터 시작
            break
    
    if start_idx is None:
        return None, None
    
    # 다음 DAY 섹션 찾기
    for i in range(day_number_idx + 3, len(lines)):
        if lines[i].strip() in [f"{d:03d}" for d in range(1, 200)]:
            end_idx = i - 2
            break
    
    section = '\n'.join(lines[start_idx:end_idx])
    # title은 start_idx에서 day_number_idx 사이의 첫 번째 비어있지 않은 줄
    title = ""
    for i in range(start_idx, min(start_idx + 3, day_number_idx)):
        if lines[i].strip() and lines[i].strip() != "DAY":
            title = lines[i].strip()
            break
    
    return section, title

def parse_dialogue_from_step3(section_text):
    """STEP3에서 Dialogue를 추출합니다."""
    dialogue = []
    lines = section_text.split('\n')
    
    # STEP3 찾기 (STEP3, STEP 3, SHEF3 등 변형 포함)
    step3_idx = None
    for i, line in enumerate(lines):
        if (('STEP' in line or 'SHEF' in line) and 
            ('3' in line or '핵심 패턴' in line or '핵심패턴' in line)):
            step3_idx = i
            break
    
    if step3_idx is None:
        return []
    
    # STEP3 이후 STEP4 전까지 파싱
    current_speaker = None
    for i in range(step3_idx + 1, len(lines)):
        line = lines[i].strip()
        
        # STEP4가 나오면 종료
        if 'STEP' in line and '4' in line:
            break
        
        # 빈 줄이나 불필요한 줄 스킵
        if not line or len(line) < 3:
            continue
        
        # A: 또는 B: 로 시작하는 줄 찾기
        if line.startswith('A:') or line.startswith('B:'):
            # 영어와 한글이 같은 줄에 있는 경우
            parts = line.split(' ', 1)
            if len(parts) > 1:
                speaker = parts[0].replace(':', '').strip()
                content = parts[1]
                
                # 영어와 한글 분리
                en_text = ""
                ko_text = ""
                
                # 마침표나 물음표로 영어 문장 찾기
                import re
                # 영어 문장 패턴 (영어로 시작하고 마침표/물음표로 끝나는 것)
                match = re.match(r'([A-Za-z,\s\'\.\?!]+)(?:\s*)(.*)$', content)
                if match:
                    en_text = match.group(1).strip()
                    ko_text = match.group(2).strip()
                
                if en_text:
                    dialogue.append({
                        "speaker": speaker,
                        "en": en_text,
                        "ko": ko_text
                    })
    
    return dialogue

def parse_patterns_from_step3(section_text):
    """STEP3에서 핵심 패턴을 추출합니다."""
    patterns = []
    lines = section_text.split('\n')
    
    # STEP3 찾기 (STEP3, STEP 3, SHEF3 등 변형 포함)
    step3_idx = None
    for i, line in enumerate(lines):
        if (('STEP' in line or 'SHEF' in line) and 
            ('3' in line or '핵심 패턴' in line or '핵심패턴' in line)):
            step3_idx = i
            break
    
    if step3_idx is None:
        return []
    
    # STEP3 이후 STEP4 전까지 패턴 찾기
    import re
    i = step3_idx + 1
    
    while i < len(lines):
        line = lines[i].strip()
        
        # STEP4가 나오면 종료
        if 'STEP' in line and '4' in line:
            break
        
        # A: 또는 B:로 시작하는 대화 줄을 찾음
        if line.startswith('A:') or line.startswith('B:'):
            # 대화 줄 다음 줄부터 다음 대화 줄이나 빈 줄이 나올 때까지 패턴 찾기
            i += 1
            pattern_candidate = ""
            
            while i < len(lines):
                next_line = lines[i].strip()
                
                # 빈 줄이거나 다음 대화 줄이 나오면 중단
                if not next_line or next_line.startswith('A:') or next_line.startswith('B:'):
                    break
                
                # STEP4가 나오면 중단
                if 'STEP' in next_line and '4' in next_line:
                    break
                
                # 패턴 설명 줄인지 확인
                has_korean = any('\uac00' <= c <= '\ud7a3' for c in next_line)
                has_english = any('a' <= c.lower() <= 'z' for c in next_line)
                
                # 한글과 영어가 모두 있고, 콜론/괄호/물결표/+가 있으면 패턴으로 간주
                if has_korean and has_english:
                    # 패턴 특징: :, ~, (, +, . 등의 기호가 있음
                    if ':' in next_line or '~' in next_line or '(' in next_line or '+' in next_line or '.' in next_line:
                        # 예문이 아닌지 확인 (예문은 보통 대문자로 시작하고 마침표로 끝남)
                        # 하지만 패턴 설명도 대문자로 시작할 수 있으므로, 
                        # 기호가 있고 길이가 적당하면 패턴으로 간주
                        is_example = re.match(r'^[A-Z][a-z]+[^:+~\(\)]+[\.\?!]\s+[가-힣]+.*[\.\?!]?\s*$', next_line)
                        if not is_example:
                            pattern_candidate = next_line
                            # 다음 줄이 한글 번역인 경우도 있으므로 확인
                            i += 1
                            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('A:') and not lines[i].strip().startswith('B:'):
                                next_next_line = lines[i].strip()
                                # 순수 한글 줄이면 패턴 설명의 일부로 간주
                                has_only_korean = all('\uac00' <= c <= '\ud7a3' or c in ' .?!,~:()-/' for c in next_next_line if c.strip())
                                if has_only_korean and len(next_next_line) > 0:
                                    # 한글 줄이 패턴의 연속인지 예문인지 확인
                                    if not re.match(r'^[가-힣\s]+[\.\?!]\s*$', next_next_line):
                                        i -= 1  # 다시 돌아감
                            
                            if pattern_candidate:
                                patterns.append(pattern_candidate)
                                pattern_candidate = ""
                            break
                
                i += 1
            
            i += 1
        else:
            i += 1
    
    return patterns

def parse_practice_from_step4(section_text):
    """STEP4에서 Practice 문제를 추출합니다."""
    practice = []
    lines = section_text.split('\n')
    
    # STEP4 찾기
    step4_idx = None
    for i, line in enumerate(lines):
        if 'STEP' in line and '4' in line:
            step4_idx = i
            break
    
    if step4_idx is None:
        return []
    
    # STEP4 이후 숫자로 시작하는 줄 찾기
    for i in range(step4_idx + 1, min(step4_idx + 20, len(lines))):
        line = lines[i].strip()
        
        # 1., 2., 3., 4. 등으로 시작하는 줄 찾기
        import re
        match = re.match(r'^(\d+)\.\s*(.+)$', line)
        if match:
            # 마지막 E 또는 공백+E 제거
            cleaned_line = re.sub(r'\s+E\s*$', '', line)
            practice.append(cleaned_line)
    
    return practice

def clean_pattern(pattern):
    """패턴을 정리합니다 (품사 표현을 ~로 치환, 콜론 정리)"""
    import re
    
    # 1. 품사 표현을 ~로 치환
    grammar_terms = [
        r'\(동사원형\)',
        r'\(동사\)',
        r'\(명사\)',
        r'\(형용사\)',
        r'\(주어\)',
        r'\(목적어\)',
        r'\(평서문\)',
        r'\(질문 어순\)',
        r'\(날/날짜/요일\)',
        r'\(날/요일\)',
        r'\(기간\)',
        r'\(장소\)',
    ]
    
    for term in grammar_terms:
        pattern = re.sub(term, '~', pattern)
    
    # 2. 콜론이 없으면 영어와 한글 사이에 추가
    if ':' not in pattern:
        # 영어 부분 끝을 찾기 (한글 직전까지)
        match = re.match(r'^([A-Za-z0-9\s\+\-\(\)\[\]\{\}\'\"/.,!?~]+?)\s+([가-힣].*)$', pattern)
        if match:
            english_part = match.group(1).strip()
            korean_part = match.group(2).strip()
            pattern = f"{english_part} : {korean_part}"
    
    # 3. 콜론 앞뒤 공백 정리
    if ':' in pattern and ' : ' not in pattern:
        pattern = re.sub(r'\s*:\s*', ' : ', pattern, count=1)
    
    return pattern

def parse_day_data(text, day_number):
    """
    특정 DAY의 데이터를 추출합니다.
    Step 3: 핵심 패턴 익히기 -> Dialogue + Patterns
    Step 4: 직접 손영작/입영작 -> Practice
    """
    # DAY 섹션 추출
    section, title = extract_day_section(text, day_number)
    
    if not section:
        print(f"  [WARNING] DAY {day_number:03d} 섹션을 찾을 수 없습니다.")
        return {
            "title": "",
            "dialogue": [],
            "patterns": [],
            "practice": []
        }
    
    # Dialogue, Patterns, Practice 추출
    dialogue = parse_dialogue_from_step3(section)
    patterns = parse_patterns_from_step3(section)
    practice = parse_practice_from_step4(section)
    
    # 패턴 정리
    patterns = [clean_pattern(p) for p in patterns]
    
    print(f"  [OK] Dialogue: {len(dialogue)}개, Patterns: {len(patterns)}개, Practice: {len(practice)}개")
    
    result = {
        "title": title,
        "dialogue": dialogue,
        "patterns": patterns,
        "practice": practice
    }
    
    return result

def main():
    pdf_path = "[B] 왕초보 영어-2024 하편.pdf"
    json_path = "data_dialog_only.json"
    
    # PDF 파일 존재 확인
    if not os.path.exists(pdf_path):
        print(f"오류: PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    print("="*70)
    print("DAY 001-130 데이터 추출 시작")
    print("="*70)
    
    # PDF 텍스트 추출
    print("\n[1/4] PDF 파일 읽기 시작...")
    pdf_text = extract_text_from_pdf(pdf_path)
    
    # PDF 텍스트를 파일로 저장
    with open("pdf_full_extracted.txt", "w", encoding="utf-8") as f:
        f.write(pdf_text)
    print("PDF 텍스트가 pdf_full_extracted.txt에 저장되었습니다.\n")
    
    # DAY 001-130 데이터 추출
    print("[2/4] DAY 001-130 데이터 추출 중...\n")
    new_data = {}
    
    # 배치 단위로 처리하여 중간 저장
    batch_size = 10
    for batch_start in range(1, 131, batch_size):
        batch_end = min(batch_start + batch_size - 1, 130)
        print(f"\n--- DAY {batch_start:03d} ~ {batch_end:03d} 처리 중 ---")
        
        for day_num in range(batch_start, batch_end + 1):
            day_key = f"DAY {day_num:03d}"
            print(f"{day_key}: ", end="")
            day_data = parse_day_data(pdf_text, day_num)
            new_data[day_key] = day_data
        
        # 중간 저장
        with open("extracted_data_temp.json", "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print(f"  -> {batch_end}개 DAY까지 중간 저장 완료")
    
    # 최종 추출 데이터 저장
    print("\n[3/4] 추출된 데이터 저장 중...")
    with open("extracted_data_full.json", "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print("추출된 데이터가 extracted_data_full.json에 저장되었습니다.")
    
    # JSON 파일 업데이트 (기존 파일 백업)
    print("\n[4/4] JSON 파일 업데이트 중...")
    if os.path.exists(json_path):
        backup_path = "data_dialog_only_backup_before_full.json"
        with open(json_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        print(f"기존 파일 백업: {backup_path}")
    
    # 새 데이터로 완전히 교체
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print(f"완료! {json_path} 파일이 DAY 001-130 데이터로 업데이트되었습니다.")
    print(f"{'='*70}")
    
    # 통계 출력
    print("\n추출 통계:")
    total_dialogues = sum(len(d['dialogue']) for d in new_data.values())
    total_patterns = sum(len(d['patterns']) for d in new_data.values())
    total_practice = sum(len(d['practice']) for d in new_data.values())
    print(f"  - 총 DAY: {len(new_data)}개")
    print(f"  - 총 Dialogue: {total_dialogues}개")
    print(f"  - 총 Patterns: {total_patterns}개")
    print(f"  - 총 Practice: {total_practice}개")
    
    # 누락된 데이터 확인
    print("\n누락 확인:")
    missing = []
    for day_num in range(1, 131):
        day_key = f"DAY {day_num:03d}"
        if day_key not in new_data or not new_data[day_key]['title']:
            missing.append(day_key)
    
    if missing:
        print(f"  경고: {len(missing)}개 DAY에 데이터가 누락되었습니다:")
        print(f"  {', '.join(missing[:10])}" + (" ..." if len(missing) > 10 else ""))
    else:
        print("  모든 DAY 데이터가 정상적으로 추출되었습니다!")

if __name__ == "__main__":
    main()

