# ===================================================================================
# TRABALHO 2: ADMINISTRAÇÃO FINANCEIRA - UFMG
# TEMA: GESTÃO DE INVESTIMENTOS & MACROECONOMIA
# APLICAÇÃO: RealReturn Finder (Analisador de Retorno Real)
#
# DESCRIÇÃO:
# Esta aplicação calcula se um investimento em ações superou a inflação (IPCA)
# em um período específico. Utiliza o conceito de "Retorno Real".
#
# FÓRMULA DE FISHER (Lógica Financeira):
# O ganho real não é apenas (Nominal - Inflação). A fórmula exata é:
# (1 + Real) = (1 + Nominal) / (1 + Inflação)
#
# FONTES DE DADOS (Captura Automática):
# 1. Ações: Yahoo Finance (via biblioteca yfinance)
# 2. Inflação: Banco Central do Brasil (API SGS - Série 433)
# ===================================================================================

from flask import Flask, render_template, request
import matplotlib
matplotlib.use('Agg') # Backend não-interativo para servidores web
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import yfinance as yf
import requests
import os
from datetime import datetime
import io

app = Flask(__name__)

# --- FUNÇÕES AUXILIARES DE CAPTURA DE DADOS ---

def get_ipca_data(start_date_str):
    """
    Busca o histórico do IPCA (Índice Oficial de Inflação) no Banco Central.
    Código da série no BCB: 433
    """
    # A API do BC aceita datas no formato DD/MM/AAAA
    date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d/%m/%Y')
    
    # URL oficial da API de Dados Abertos do BCB
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={formatted_date}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Transforma em DataFrame do Pandas para facilitar cálculos
        df_ipca = pd.DataFrame(data)
        df_ipca['data'] = pd.to_datetime(df_ipca['data'], format='%d/%m/%Y')
        df_ipca['valor'] = pd.to_numeric(df_ipca['valor'])
        
        # O IPCA vem em % ao mês (ex: 0.53). Dividimos por 100 para cálculo (0.0053)
        df_ipca['valor'] = df_ipca['valor'] / 100
        
        return df_ipca
    except Exception as e:
        print(f"Erro ao buscar IPCA: {e}")
        return pd.DataFrame() # Retorna vazio em caso de erro

def generate_analysis(ticker, start_date, initial_amount):
    """
    Executa o núcleo do trabalho: cruza dados de mercado com dados econômicos.
    """
    # 1. CAPTURA DE DADOS DE AÇÃO (YFINANCE)
    # Adiciona '.SA' se o usuário esquecer, para garantir que busque no Brasil
    if not ticker.upper().endswith('.SA') and len(ticker) < 6: 
        ticker = ticker + '.SA'
    
    # Baixa dados diários
    stock_df = yf.download(ticker, start=start_date, progress=False)
    
    if stock_df.empty:
        raise ValueError(f"Não foram encontrados dados para {ticker}. Verifique o código ou a data.")

    # Usamos 'Adj Close' pois considera dividendos reinvestidos (retorno total)
    # Se 'Adj Close' não existir (mudança recente do yfinance), usa 'Close'
    col_name = 'Adj Close' if 'Adj Close' in stock_df.columns else 'Close'
    stock_series = stock_df[col_name]

    # Se o retorno do yfinance vier como DataFrame multi-index, converte para Series simples
    if isinstance(stock_series, pd.DataFrame):
        stock_series = stock_series.iloc[:, 0]

    # 2. CÁLCULO DO RETORNO NOMINAL (Do Investimento)
    # Normaliza: Quantas cotas eu compraria com o valor inicial?
    initial_price = float(stock_series.iloc[0])
    num_shares = initial_amount / initial_price
    
    # Cria uma série de "Patrimônio ao longo do tempo"
    portfolio_series = stock_series * num_shares
    
    # 3. CAPTURA E PROCESSAMENTO DA INFLAÇÃO (BCB)
    df_ipca = get_ipca_data(start_date)
    
    # Lógica Financeira Complexa:
    # A inflação é mensal, mas a ação é diária. Precisamos criar uma curva de inflação diária
    # para comparar no gráfico. Faremos isso criando um índice acumulado.
    
    # Cria um índice base 1.0
    df_ipca['fator'] = 1 + df_ipca['valor']
    # Acumula o produtório (Juros compostos da inflação)
    cumulative_ipca = df_ipca['fator'].cumprod()
    
    # Cria um DataFrame diário para inflação reamostrando os dados mensais
    # Isso suaviza a curva de inflação para o gráfico ficar bonito
    inflation_curve = pd.Series(index=stock_series.index, data=None)
    
    # Mapeia os valores mensais para as datas correspondentes
    # (Lógica simplificada para fins didáticos: assume inflação constante no mês)
    current_inf_idx = initial_amount
    inflation_values = []
    
    # Construção manual da curva de inflação ajustada ao valor investido
    # Se IPCA acumulado foi 10%, o valor corrigido deve ser R$ 1100
    
    # Pegamos a inflação acumulada total do período
    if not df_ipca.empty:
        total_inflation = df_ipca['fator'].prod() - 1
    else:
        total_inflation = 0

    # Valor Final Corrigido pelo IPCA
    amount_inflation_adjusted = initial_amount * (1 + total_inflation)
    
    # Valor Final do Investimento
    final_amount = float(portfolio_series.iloc[-1])
    
    # 4. CÁLCULO DO RETORNO REAL (Fisher)
    nominal_return = (final_amount - initial_amount) / initial_amount
    real_return = ((1 + nominal_return) / (1 + total_inflation)) - 1

    # --- GERAÇÃO DO GRÁFICO ---
    plt.style.use('bmh') # Estilo visual limpo e profissional
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plota a evolução do dinheiro investido
    ax.plot(portfolio_series.index, portfolio_series.values, 
            label=f'Seu Investimento ({ticker})', color='#25146E', linewidth=2)
    
    # Para plotar a linha da inflação, faremos uma linha reta simples entre 
    # o valor inicial e o valor final corrigido (aproximação visual suficiente para o trabalho)
    ax.plot([portfolio_series.index[0], portfolio_series.index[-1]], 
            [initial_amount, amount_inflation_adjusted], 
            label='Inflação Acumulada (IPCA)', color='#D9534F', linestyle='--', linewidth=2)

    # Formatação
    ax.set_title(f"Batalha Real: {ticker} vs Inflação (IPCA)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Saldo Financeiro (R$)", fontsize=12)
    ax.legend()
    
    # Formata eixo X para datas legíveis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    plt.xticks(rotation=45)
    
    # Área de preenchimento para destacar ganho ou perda
    # Se ganhou (Verde), se perdeu (Vermelho)
    if final_amount > amount_inflation_adjusted:
        ax.fill_between(portfolio_series.index, portfolio_series.values, 
                        [initial_amount + ((amount_inflation_adjusted-initial_amount)*(i/len(portfolio_series))) for i in range(len(portfolio_series))],
                        where=(portfolio_series.values > initial_amount), alpha=0.1, color='green')

    plt.tight_layout()
    
    # Salva
    if not os.path.exists('static'):
        os.makedirs('static')
    chart_filename = f'chart_{ticker}_{int(datetime.now().timestamp())}.png'
    plt.savefig(os.path.join('static', chart_filename))
    plt.close(fig)
    
    # Retorna dicionário com todos os resultados para o HTML
    return {
        'chart': chart_filename,
        'final_amount': final_amount,
        'amount_adjusted': amount_inflation_adjusted,
        'nominal_return': nominal_return * 100,
        'inflation_total': total_inflation * 100,
        'real_return': real_return * 100,
        'is_profit': real_return > 0
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    error = None
    
    if request.method == 'POST':
        try:
            ticker = request.form.get('ticker').upper().strip()
            start_date = request.form.get('start_date')
            amount = float(request.form.get('amount'))
            
            if not ticker or not start_date or not amount:
                raise ValueError("Preencha todos os campos.")
                
            # Chama a função principal de lógica
            results = generate_analysis(ticker, start_date, amount)
            results['ticker'] = ticker
            
        except Exception as e:
            error = str(e)
            
    return render_template('index.html', results=results, error=error)

if __name__ == '__main__':
    app.run(debug=True, port=5002)