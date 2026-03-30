import json
import copy
import os

input_path = r'C:\dev\project\SKN27-2nd-1TEAM\notebook\hwan_model_2.ipynb'
out1_path = r'C:\dev\project\SKN27-2nd-1TEAM\notebook\hwan_1_preprocessing.ipynb'
out2_path = r'C:\dev\project\SKN27-2nd-1TEAM\notebook\hwan_2_modeling.ipynb'
csv_path = r'C:\dev\project\SKN27-2nd-1TEAM\data\hwan_preprocessed_data.csv'

def main():
    if not os.path.exists(input_path):
        print("에러:", input_path, "를 찾을 수 없습니다.")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # 파생 변수 로직이 담긴 첫 번째 코드 셀 탐색
    first_code_idx = 0
    for i, cell in enumerate(nb.get('cells', [])):
        if cell.get('cell_type') == 'code':
            first_code_idx = i
            break

    # ====================================================
    # 1. 전처리용 첫 번째 노트북 (hwan_1_preprocessing.ipynb)
    # ====================================================
    nb1 = copy.deepcopy(nb)
    # 첫 번째 코드 셀(+앞에 있는 마크다운)까지만 유지
    nb1['cells'] = nb['cells'][:first_code_idx+1]
    
    # 마지막 결과값을 내보내는 셀 자동 추가
    save_csv_cell = {
       "cell_type": "code",
       "execution_count": None,
       "metadata": {},
       "outputs": [],
       "source": [
        "# [자동 추가됨] 대규모 전처리가 완료된 DataFrame을 모델링 파일에서 쓰도록 내보냅니다.\n",
        "import os\n",
        "csv_path = r'C:\\dev\\project\\SKN27-2nd-1TEAM\\data\\hwan_preprocessed_data.csv'\n",
        "os.makedirs(os.path.dirname(csv_path), exist_ok=True)\n",
        "df.to_csv(csv_path, index=False)\n",
        "print(f'✅ 전처리 완료 데이터가 성공적으로 저장되었습니다! 저장 경로: {csv_path}')\n"
       ]
    }
    nb1['cells'].append(save_csv_cell)

    with open(out1_path, 'w', encoding='utf-8') as f:
        json.dump(nb1, f, indent=1)

    # ====================================================
    # 2. 모델링용 두 번째 노트북 (hwan_2_modeling.ipynb)
    # ====================================================
    nb2 = copy.deepcopy(nb)
    
    load_csv_cell = {
       "cell_type": "code",
       "execution_count": None,
       "metadata": {},
       "outputs": [],
       "source": [
        "# [자동 추가됨] 1번 프프로세싱 노트북에서 정제한 데이터를 1초 만에 불러옵니다.\n",
        "import pandas as pd\n",
        "csv_path = r'C:\\dev\\project\\SKN27-2nd-1TEAM\\data\\hwan_preprocessed_data.csv'\n",
        "try:\n",
        "    df = pd.read_csv(csv_path)\n",
        "    print('✅ 안전 확보: 정제된 40+ 피처 데이터를 불러왔습니다. 형상:', df.shape)\n",
        "except FileNotFoundError:\n",
        "    print('❌ 에러: hwan_1_preprocessing.ipynb를 먼저 [모두 실행(Run All)] 하여 csv 파일을 생성해주세요.')\n"
       ]
    }
    
    # 데이터를 불러오는 셀을 제일 상단에 꽂아넣고, 이어서 나머지 모든 모델링 셀 추가
    nb2['cells'] = [load_csv_cell] + nb['cells'][first_code_idx+1:]

    with open(out2_path, 'w', encoding='utf-8') as f:
        json.dump(nb2, f, indent=1)

    print("✅ 주피터 노트북 무결성 분할 처리 완료: [hwan_1_preprocessing.ipynb] & [hwan_2_modeling.ipynb]")

if __name__ == "__main__":
    main()
