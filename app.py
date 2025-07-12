import streamlit as st
import csv
import io
import re
from datetime import datetime

st.set_page_config(page_title="Busca WhatsApp com Filtros", layout="wide")
st.title("📲 Busca de Conversas com Filtros Avançados")

def extrair_data_autor(linha):
    match = re.match(r'^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}) - (.*?):', linha)
    if match:
        data = match.group(1)
        autor = match.group(2)
        try:
            dt = datetime.strptime(data, '%d/%m/%Y %H:%M')
        except:
            dt = None
        return dt, autor
    return None, None

def buscar_ocorrencias_anteriores(conteudo, termo_busca, linhas_anteriores=10, linhas_posteriores=0, usar_regex=False):
    linhas = conteudo.splitlines()
    resultados = []

    for i, linha in enumerate(linhas):
        encontrou = False
        if usar_regex:
            if re.search(termo_busca, linha, re.IGNORECASE):
                encontrou = True
        else:
            if termo_busca.lower() in linha.lower():
                encontrou = True

        if encontrou:
            inicio = max(0, i - linhas_anteriores)
            fim = min(len(linhas), i + linhas_posteriores + 1)
            bloco = [linhas[j].strip() for j in range(inicio, fim)]
            data, autor = extrair_data_autor(linha)
            resultados.append({
                'linha_original': i + 1,
                'bloco': bloco,
                'data': data,
                'autor': autor
            })
    return resultados

def aplicar_filtros(resultados, autores_sel, data_ini, data_fim, palavras_adic):
    filtrados = []
    for r in resultados:
        if r['autor'] and autores_sel and r['autor'] not in autores_sel:
            continue
        if r['data']:
            if data_ini and r['data'] < data_ini:
                continue
            if data_fim and r['data'] > data_fim:
                continue
        if palavras_adic:
            bloco_texto = ' '.join(r['bloco']).lower()
            if not all(p.lower() in bloco_texto for p in palavras_adic):
                continue
        filtrados.append(r)
    return filtrados

def gerar_csv(resultados, linhas_anteriores, linhas_posteriores):
    output_str = io.StringIO()
    writer = csv.writer(output_str)

    total_linhas = linhas_anteriores + 1 + linhas_posteriores
    header = ['Linha no Arquivo', 'Data', 'Autor'] \
             + [f"Linha -{i}" for i in range(linhas_anteriores, 0, -1)] \
             + ['Linha com ocorrência'] \
             + [f"Linha +{i}" for i in range(1, linhas_posteriores + 1)]
    writer.writerow(header)

    for r in resultados:
        bloco = r['bloco']
        bloco_completo = [''] * (total_linhas - len(bloco)) + bloco
        row = [r['linha_original'],
               r['data'].strftime('%d/%m/%Y %H:%M') if r['data'] else '',
               r['autor'] or ''] + bloco_completo
        writer.writerow(row)

    output_bytes = io.BytesIO()
    output_bytes.write(output_str.getvalue().encode('utf-8'))
    output_bytes.seek(0)
    return output_bytes

# Interface
uploaded_file = st.file_uploader("📄 Envie um arquivo de texto (.txt)", type="txt")
termo = st.text_input("🔍 Digite a string ou regex a ser buscada")
usar_regex = st.checkbox("Usar expressão regular?", value=False)
linhas_anteriores = st.slider("📏 Linhas anteriores a incluir", 1, 50, 10)
linhas_posteriores = st.slider("📐 Linhas posteriores a incluir", 0, 50, 0)

if uploaded_file and termo:
    conteudo = uploaded_file.read().decode('utf-8')
    resultados = buscar_ocorrencias_anteriores(
        conteudo, termo, linhas_anteriores, linhas_posteriores, usar_regex
    )

    st.success(f"🔎 {len(resultados)} ocorrência(s) encontradas.")

    if resultados:
        autores_unicos = sorted(set(r['autor'] for r in resultados if r['autor']))
        datas_validas = [r['data'] for r in resultados if r['data']]
        data_min, data_max = (min(datas_validas), max(datas_validas)) if datas_validas else (None, None)

        with st.expander("🧰 Filtros adicionais"):
            autores_sel = st.multiselect("👤 Filtrar por autor", autores_unicos, default=autores_unicos)
            data_ini = st.date_input("📅 Data inicial", data_min.date() if data_min else None)
            data_fim = st.date_input("📅 Data final", data_max.date() if data_max else None)
            palavras_adic = st.text_input("🔤 Palavras-chave adicionais (separadas por vírgula)").split(',')

        data_ini_dt = datetime.combine(data_ini, datetime.min.time()) if data_ini else None
        data_fim_dt = datetime.combine(data_fim, datetime.max.time()) if data_fim else None

        palavras_adic = [p.strip() for p in palavras_adic if p.strip()]
        resultados_filtrados = aplicar_filtros(resultados, autores_sel, data_ini_dt, data_fim_dt, palavras_adic)

        st.info(f"🎯 {len(resultados_filtrados)} ocorrência(s) após filtro.")

        if resultados_filtrados:
            with st.expander("👁️ Ver ocorrências filtradas"):
                for idx, r in enumerate(resultados_filtrados):
                    st.markdown(f"**Ocorrência #{idx + 1}** — Linha `{r['linha_original']}` — {r['data']} — {r['autor']}")
                    st.code('\n'.join(r['bloco']), language='text')

            csv_data = gerar_csv(resultados_filtrados, linhas_anteriores, linhas_posteriores)

            st.download_button(
                label="⬇️ Baixar resultados filtrados (.csv)",
                data=csv_data,
                file_name=f"resultados_filtrados_{termo.replace(' ', '_')}.csv",
                mime='text/csv'
            )
        else:
            st.warning("Nenhuma ocorrência após aplicar os filtros.")
