# App de Finanças da Casa

## Arquivos
- `app_financas_pessoais.py`
- `requirements_financas_pessoais.txt`

## Rodar localmente
```bash
pip install -r requirements_financas_pessoais.txt
streamlit run app_financas_pessoais.py
```

## O que o app faz
- Cadastra receitas e despesas
- Separa despesas fixas e variáveis
- Calcula saldo do mês
- Mostra dashboard com gráficos
- Salva tudo localmente em SQLite, sem precisar subir Excel

## Banco de dados
Ao executar pela primeira vez, o app cria automaticamente o arquivo `financas_casa.db` na mesma pasta do app.
