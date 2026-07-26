# 🏋️ Gym Tracker AI

> **Sistema Inteligente de Prescrição, Registro de Execução e Sobrecarga Progressiva de Treinos impulsionado por Inteligência Artificial.**

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org/)
[![Groq AI](https://img.shields.io/badge/Groq%20AI-Llama%203.3--70B-orange.svg)](https://groq.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📌 Sobre o Projeto

O **Gym Tracker AI** é uma plataforma completa desenvolvida para atletas, praticantes de musculação e personal trainers. O sistema combina o poder de Modelos de Linguagem de Grande Porte (LLMs via Groq/Llama-3.3-70B) e visão computacional (EasyOCR) para criar, revisar, acompanhar e evoluir treinos de musculação com rigor fisiológico e metodológico.

---

## ✨ Funcionalidades Principais

* 🤖 **Geração Inteligente com Perfil do Treinador**: Prescrição automatizada baseada no objetivo do aluno (Hipertrofia, Força, Resistência, HIIT, Funcional, Reabilitação, Emagrecimento, CrossFit), nível e filosofia de treino do professor.
* 📷 **Reconhecimento OCR de Imagens de Fichas**: Leitura automatizada de fotos de treinos e fichas físicas via EasyOCR, convertendo imagens em dados estruturados.
* 🧱 **Arquitetura Metodológica de 3 Blocos**:
  * **Bloco 1 (Warm-up / Mobilidade)**: Preparação articular, liberação miofascial e ativação neuromuscular.
  * **Bloco 2 (Main Session)**: Exercícios compostos e isolados principais com volume e carga calculados.
  * **Bloco 3 (Cool-down / Recovery)**: Volta à calma, respiração diafragmática e descompressão espinhal.
* ✏️ **Edição Pré-Salvamento**: Ajuste fino de séries, repetições, carga sugerida e métodos de treinamento antes da confirmação final no histórico.
* 🔴 **Modo Treino ao Vivo**: Execução em tempo real na academia — registro série a série (carga, reps e RPE individuais), cronômetro automático de descanso entre séries e checklist de progresso por exercício. Ao finalizar, consolida os dados no histórico e na sobrecarga progressiva.
* 📝 **Registro Real de Execução (Pós-Treino)**: Captura precisa dos dados executados na academia: Carga Real (kg), Repetições Reais e Percepção Subjetiva de Esforço (**RPE** na escala de 1.0 a 10.0). Alternativa em formato resumido para quem prefere registrar tudo de uma vez, depois do treino.
* 📈 **Sobrecarga Progressiva Automática**: Algoritmo que analisa o histórico recente de RPE e desempenho real para sugerir incrementos estratégicos (+2.5kg em isolados / +5.0kg em compostos) com **trava de segurança de 120%**.
* 📄 **Exportação de PDF Print-Friendly**: Geração instantânea de fichas de treino limpas em PDF formatadas em A4 para impressão física, com colunas para anotação a caneta/lápis e destaque para alertas de risco do treinador.
* 📊 **Analytics e Gráficos de Volume**: Dashboard visual para monitoramento do volume total acumulado (séries x repetições x carga).

---

## 🛠️ Tecnologias Utilizadas

### **Backend**
* **Python 3.11+**
* **FastAPI**: Framework web assíncrono de alta performance.
* **SQLAlchemy 2.0 (ORM)**: Mapeamento objeto-relacional com suporte completo a anotações de tipo `Mapped[...]`.
* **Pydantic V2**: Validação estrita de dados e schemas de requisição/resposta.
* **SQLite**: Banco de dados relacional embutido.

### **Inteligência Artificial & Visão Computacional**
* **Groq API (Llama-3.3-70B-versatile)**: Geração de treinos estruturados em JSON estrito.
* **EasyOCR & PyTorch**: Extração de texto e números em imagens de treinos físicos.

### **Frontend & Visualização**
* **HTML5 & Vanilla CSS3**: Interface responsiva, com dark/light gradients, cards dinâmicos e modais interativos.
* **html2pdf.js**: Motor client-side para geração e download de arquivos PDF.
* **Plotly.js**: Renderização de gráficos interativos de volume e evolução.

---

## 📂 Estrutura do Projeto

```text
gym-tracker/
├── app/
│   ├── main.py                  # Ponto de entrada FastAPI e rotas estáticas
│   ├── models.py                # Modelos ORM SQLAlchemy (Workout, Exercise, WorkoutProgress)
│   ├── schemas.py               # Schemas Pydantic de validação
│   ├── database.py              # Configuração da conexão SQLite
│   ├── routers/
│   │   ├── workout.py           # Endpoints de treino, edição, registro real, PDF e visualizações
│   │   ├── image.py             # Endpoint de Upload e OCR de imagem
│   │   ├── analytics.py         # Endpoints de gráficos de evolução
│   │   └── live_session.py      # Endpoints do Modo Treino ao Vivo (séries individuais)
│   ├── services/
│   │   ├── llm_service.py       # Integração com Groq LLM e prompts metodológicos
│   │   ├── progression_service.py # Algoritmo de Sobrecarga Progressiva e Trava de 120%
│   │   └── workout_service.py   # Lógica compartilhada de aplicação de execução real
│   └── static/
│       └── dashboard.html       # Painel Web interativo da aplicação
├── specs/                       # Especificações técnicas e planos Speckit
├── tests/                       # Suíte de testes automatizados com pytest
│   ├── test_execution_logging.py
│   ├── test_progression.py
│   └── test_pdf_export.py
├── .env                         # Variáveis de ambiente (GROQ_API_KEY)
├── requirements.txt             # Dependências do projeto
└── README.md                    # Documentação principal
```

---

## 🚀 Como Executar o Projeto

### **Pré-requisitos**
* Python 3.11 ou superior instalado.
* Uma chave de API da [Groq](https://console.groq.com/).

### **1. Clonar o Repositório**
```bash
git clone https://github.com/Gegeu-sp/gymtracker_AI.git
cd gymtracker_AI
```

### **2. Criar e Ativar o Ambiente Virtual**
* **Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
* **Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### **3. Instalar as Dependências**
```bash
pip install -r requirements.txt
```

### **4. Configurar as Variáveis de Ambiente**
Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```env
GROQ_API_KEY=sua_chave_api_groq_aqui
```

### **5. Executar o Servidor**
```bash
uvicorn app.main:app --reload
```

A aplicação estará disponível em:
* 🏠 **Dashboard Web:** [http://localhost:8000/](http://localhost:8000/)
* 📚 **Documentação Interativa (Swagger API):** [http://localhost:8000/docs](http://localhost:8000/docs)
* 📋 **Tabela de Histórico de Treinos:** [http://localhost:8000/workouts/view](http://localhost:8000/workouts/view)

---

## 🧪 Executando os Testes Automatizados

Para rodar a suíte completa de testes integrativos e unitários com o `pytest`:

```bash
python -m pytest
```

---

## 📄 Licença

Este projeto está licenciado sob a licença [MIT](LICENSE).
