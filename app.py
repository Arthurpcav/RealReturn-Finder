# ===================================================================================
# TRABALHO 2: ADMINISTRAÇÃO FINANCEIRA - UFMG
# TEMA: GESTÃO DE INVESTIMENTOS 
# ALUNOS: Arthur Pereira Carvalho e Davi Carvalho dos Santos
#
# APLICAÇÃO: RealReturn Finder (Analisador de Retorno Real)
#
# DESCRIÇÃO:
# Esta aplicação realiza uma análise cruzada entre o mercado de capitais e
# indicadores macroeconômicos para determinar a real rentabilidade de um ativo.
# O foco central é distinguir o ganho nominal do ganho real.
#
# 1.  RETORNO NOMINAL: O crescimento bruto do valor investido, considerando
#     a valorização da cotação do ativo ao longo do tempo.
#
# 2.  RETORNO REAL (FÓRMULA DE FISHER): Ajusta o retorno nominal descontando
#     a perda do poder de compra causada pela inflação (IPCA).
#     Diferente da subtração simples (Nominal - Inflação), utilizamos a
#     fórmula exata de Fisher: (1 + Real) = (1 + Nominal) / (1 + Inflação).
#     Isso revela se o investidor realmente aumentou seu patrimônio ou apenas
#     reposicionou seu poder de compra.
# ===================================================================================

#importações necessárias
from flask import Flask, render_template, request
import matplotlib
matplotlib.use('Agg') #configura o Matplotlib para rodar em background, essencial para servidores web sem monitor
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import yfinance as yf #biblioteca para extração de dados do mercado financeiro (Yahoo Finance)
import requests
import os
from datetime import datetime
import io

#inicialização da aplicação Flask
app = Flask(__name__)

#função auxiliar para Captura de Dados Macroeconômicos
def get_ipca_data(start_date_str):
    """
    Busca o histórico do IPCA (Índice Oficial de Inflação) via API do Banco Central.
    Série Temporal 433: Índice nacional de preços ao consumidor amplo (IPCA).

    Args:
        start_date_str (str): Data de início da análise no formato 'YYYY-MM-DD'.

    Returns:
        pd.DataFrame: DataFrame contendo as datas e as taxas mensais de inflação.
    """
    #formatação da data para o padrão exigido pela API do Banco Central (DD/MM/AAAA)
    date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d/%m/%Y')
    
    #montagem da URL da API de Dados Abertos do BCB
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={formatted_date}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() #verifica se a requisição HTTP foi bem-sucedida
        data = response.json()
        
        #processamento dos dados:
        #1 - Converte o JSON bruto para um DataFrame estruturado
        df_ipca = pd.DataFrame(data)
        #2 - Converte a coluna de data para objetos datetime para permitir ordenação e plotagem
        df_ipca['data'] = pd.to_datetime(df_ipca['data'], format='%d/%m/%Y')
        #3 - Converte os valores de string para numérico (float)
        df_ipca['valor'] = pd.to_numeric(df_ipca['valor'])
        
        #ajuste matemático: O IPCA vem em percentual (ex: 0.53). Dividimos por 100
        #para obter o fator decimal (0.0053) necessário para os cálculos financeiros.
        df_ipca['valor'] = df_ipca['valor'] / 100
        
        return df_ipca
    except Exception as e:
        #em caso de falha na conexão com o BCB, retorna um dataframe vazio para evitar crash
        print(f"Erro ao buscar IPCA: {e}")
        return pd.DataFrame() # Retorna vazio em caso de erro

#função principal de Análise e Geração de Relatório
def generate_analysis(ticker, start_date, initial_amount):
    """
    Executa o cruzamento de dados de mercado (Ações) com dados econômicos (Inflação)
    para calcular o Retorno Real segundo a hipótese de Fisher.

    Args:
        ticker (str): O código do ativo (ex: PETR4).
        start_date (str): Data inicial do investimento.
        initial_amount (float): Valor monetário inicial investido.

    Returns:
        dict: Um dicionário contendo estatísticas financeiras e o nome do gráfico gerado.
    """
    # 1. CAPTURA DE DADOS DE MERCADO (YFINANCE)
    # Garante a formatação correta do ticker para o mercado brasileiro (.SA)
    if not ticker.upper().endswith('.SA') and len(ticker) < 6: 
        ticker = ticker + '.SA'
    
    #baixa os dados históricos diários da ação
    stock_df = yf.download(ticker, start=start_date, progress=False)
    
    if stock_df.empty:
        raise ValueError(f"Não foram encontrados dados para {ticker}. Verifique o código ou a data.")

    #seleção da coluna de preço:
    #'Adj Close' é preferível pois já desconta dividendos e desdobramentos (Retorno Total)
    col_name = 'Adj Close' if 'Adj Close' in stock_df.columns else 'Close'
    stock_series = stock_df[col_name]

    #normalização: se o yfinance retornar um MultiIndex, simplificamos para Series
    if isinstance(stock_series, pd.DataFrame):
        stock_series = stock_series.iloc[:, 0]

    #CONCEITO FINANCEIRO: Evolução Patrimonial
    #Para simular o investimento, calculamos quantas cotas poderiam ser compradas
    #com o valor inicial na data de partida. O patrimônio futuro é: Cotas * Preço Atual.
    initial_price = float(stock_series.iloc[0])
    num_shares = initial_amount / initial_price
    
    portfolio_series = stock_series * num_shares
    
    # 2. PROCESSAMENTO DA INFLAÇÃO (Benchmarking)
    df_ipca = get_ipca_data(start_date)
    
    #cálculo de juros compostos da inflação:
    #Transformamos a taxa mensal em fator (ex: 1.0053) e acumulamos o produto
    #para saber a inflação total acumulada no período.
    df_ipca['fator'] = 1 + df_ipca['valor']
    #acumula o produtório (Juros compostos da inflação)
    cumulative_ipca = df_ipca['fator'].cumprod()
    
    #cria um DataFrame diário para inflação reamostrando os dados mensais
    #isso suaviza a curva de inflação para o gráfico ficar bonito
    inflation_curve = pd.Series(index=stock_series.index, data=None)
    
    #mapeia os valores mensais para as datas correspondentes
    #(lógica simplificada para fins didáticos: assume inflação constante no mês)
    current_inf_idx = initial_amount
    inflation_values = []
    
    #construção manual da curva de inflação ajustada ao valor investido
    #se IPCA acumulado foi 10%, o valor corrigido deve ser R$ 1100
    
    #pegamos a inflação acumulada total do período
    if not df_ipca.empty:
        #subtrai 1 no final para voltar à forma percentual (ex: 1.10 -> 0.10 ou 10%)
        total_inflation = df_ipca['fator'].prod() - 1
    else:
        total_inflation = 0

    #CONCEITO: Correção Monetária
    #calculamos quanto o dinheiro inicial valeria hoje apenas corrigido pela inflação.
    #este é o "ponto de empate" em termos reais.
    amount_inflation_adjusted = initial_amount * (1 + total_inflation)
    
    #valor Final do Investimento
    final_amount = float(portfolio_series.iloc[-1])
    
    #CONCEITO FINANCEIRO: FÓRMULA DE FISHER (Retorno Real)
    #calcula o ganho acima da inflação.
    #1 - Retorno Nominal: Variação bruta do investimento
    nominal_return = (final_amount - initial_amount) / initial_amount
    #2 - Retorno Real: A fórmula de Fisher desconta a inflação do retorno nominal
    #Fórmula: (1 + r_real) = (1 + r_nominal) / (1 + i_inflacao)
    real_return = ((1 + nominal_return) / (1 + total_inflation)) - 1

    # --- GERAÇÃO DO GRÁFICO ---
    plt.style.use('bmh') #define um estilo limpo e profissional para relatórios financeiros
    fig, ax = plt.subplots(figsize=(12, 7))
    
    #plota a curva de evolução do patrimônio (Investimento)
    ax.plot(portfolio_series.index, portfolio_series.values, 
            label=f'Seu Investimento ({ticker})', color='#25146E', linewidth=2)
    
    #plota a linha de referência da inflação (Benchmark)
    #desenhamos uma linha reta entre o valor inicial e o valor corrigido
    #para representar a perda de poder de compra ao longo do tempo
    ax.plot([portfolio_series.index[0], portfolio_series.index[-1]], 
            [initial_amount, amount_inflation_adjusted], 
            label='Inflação Acumulada (IPCA)', color='#D9534F', linestyle='--', linewidth=2)

    #configurações de legibilidade do gráfico
    ax.set_title(f"Batalha Real: {ticker} vs Inflação (IPCA)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Saldo Financeiro (R$)", fontsize=12)
    ax.legend()
    
    #formata o eixo X para exibir datas de forma legível (Mês/Ano)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
    plt.xticks(rotation=45)
    
    #destaque visual de Lucro/Prejuízo Real
    #pinta a área entre as curvas de verde (ganho real) ou vermelho (perda real)
    #isso facilita a interpretação visual imediata pelo usuário
    if final_amount > amount_inflation_adjusted:
        ax.fill_between(portfolio_series.index, portfolio_series.values, 
                        [initial_amount + ((amount_inflation_adjusted-initial_amount)*(i/len(portfolio_series))) for i in range(len(portfolio_series))],
                        where=(portfolio_series.values > initial_amount), alpha=0.1, color='green')

    plt.tight_layout()
    
    #salva a imagem gerada na pasta estática
    if not os.path.exists('static'):
        os.makedirs('static')
    chart_filename = f'chart_{ticker}_{int(datetime.now().timestamp())}.png'
    plt.savefig(os.path.join('static', chart_filename))
    plt.close(fig) #libera memória
    
    #retorna um dicionário estruturado com os resultados para exibição no front-end
    return {
        'chart': chart_filename,
        'final_amount': final_amount,
        'amount_adjusted': amount_inflation_adjusted,
        'nominal_return': nominal_return * 100,
        'inflation_total': total_inflation * 100,
        'real_return': real_return * 100,
        'is_profit': real_return > 0
    }

#rota principal da aplicação
@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Controlador principal: recebe os dados do formulário, orquestra a análise
    financeira e renderiza os resultados.
    """
    results = None
    error = None
    
    #verifica se o formulário foi submetido
    if request.method == 'POST':
        try:
            #captura e higieniza os dados de entrada
            ticker = request.form.get('ticker').upper().strip()
            start_date = request.form.get('start_date')
            amount = float(request.form.get('amount'))
            
            #validação básica de entrada
            if not ticker or not start_date or not amount:
                raise ValueError("Preencha todos os campos.")
                
            #chama a função core para processar a análise
            results = generate_analysis(ticker, start_date, amount)
            results['ticker'] = ticker
            
        except Exception as e:
            #captura erros de execução (ex: ticker não encontrado, erro na API do BC)
            error = str(e)
            
    return render_template('index.html', results=results, error=error)

#ponto de entrada da aplicação
if __name__ == '__main__':
    #inicia o servidor em modo debug na porta 5002
    app.run(debug=True, port=5002)