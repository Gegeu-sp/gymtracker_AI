from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from .database import engine, Base, run_startup_migrations
from .routers import workout, image, analytics, live_session, extraction, assessment

# Criar tabelas no banco de dados
Base.metadata.create_all(bind=engine)
# Aplica colunas novas em tabelas já existentes (sem Alembic, ver app/database.py)
run_startup_migrations()

app = FastAPI(
    title="Gym Tracker AI",
    description="Sistema inteligente de geração e acompanhamento de treinos",
    version="1.0"
)

# Montar arquivos estáticos (para servir o HTML da dashboard)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Incluir os roteadores (endpoints da API)
app.include_router(workout.router)
app.include_router(image.router)
app.include_router(analytics.router)
app.include_router(live_session.router)
app.include_router(extraction.router)
app.include_router(assessment.router)

# Rota principal: serve a Dashboard HTML
@app.get("/")
def dashboard():
    return FileResponse("app/static/dashboard.html")

# Página de Extração de Referência
@app.get("/extraction")
def extraction_page():
    return FileResponse("app/static/extraction.html")

# Página de Avaliação Adolescente <-- NOVO
@app.get("/assessment")
def assessment_page():
    return FileResponse("app/static/assessment.html")

# Redireciona a rota antiga (versão PROESP-BR, removida na consolidação da Avaliação Física)
# para a nova, pra não deixar bookmarks/abas salvas de antes darem 404.
@app.get("/assessments/view")
@app.get("/assessments")
def assessment_page_redirect():
    return RedirectResponse(url="/assessment")

# Rota de verificação de saúde do sistema
@app.get("/health")
def health():
    return {"status": "ok", "message": "🏋️ Gym Tracker AI está rodando!"}