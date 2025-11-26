<div align="center">
  <h1 style="color: #25146E; border-bottom: 2px solid #EAEBFF; padding-bottom: 10px;">
    Análise Real de Investimentos – Ações vs Inflação (IPCA)
  </h1>
</div>

### Visão Geral

O **RealReturn Finder** é uma aplicação web refinada e didática, desenvolvida para analisar se um investimento em ações realmente superou a inflação brasileira (IPCA) ao longo de um período escolhido.  
A ferramenta combina:

- Dados de mercado (Yahoo Finance – preços ajustados)
- Dados macroeconômicos oficiais (IPCA – Banco Central do Brasil, Série 433)
- Cálculo financeiro correto baseado na **Equação de Fisher**

O sistema exibe um gráfico comparando **o valor acumulado do investimento** com **o valor corrigido pela inflação**, destacando visualmente ganho real ou perda real. Tudo ocorre de forma automática, a partir da data e do ticker informados pelo usuário.

![Screenshot da Aplicação](./screenshot.png)
---

### 🚀 Como Executar

Siga os 3 passos abaixo para configurar e rodar o projeto.

#### **1. Clone o Repositório**
Abra seu terminal, navegue até o diretório onde deseja salvar o projeto e execute o comando:
```bash
git clone https://github.com/Arthurpcav/RealReturn-Finder.git
cd RealReturn-Finder
```

#### **2. Instale as Dependências**
-   Instale todas as bibliotecas necessárias com um único comando:
    ```bash
    python -m pip install -r requirements.txt
    ```

#### **3. Execute a Aplicação**
-   Inicie o servidor:
    ```bash
    python app.py
    ```
-   Abra seu navegador e acesse o endereço abaixo para ver a aplicação funcionando:
    > **[http://127.0.0.1:5001](http://127.0.0.1:5002)**