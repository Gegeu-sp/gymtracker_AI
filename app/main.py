from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse  # <-- CORREÇÃO AQUI (era FileResponse, não File)
from .database import engine, Base, run_startup_migrations
from .routers import workout, image, analytics, live_session

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

# Rota principal: serve a Dashboard HTML
@app.get("/")
def dashboard():
    return FileResponse("app/static/dashboard.html")

# Rota de verificação de saúde do sistema
@app.get("/health")
def health():
    return {"status": "ok", "message": "🏋️ Gym Tracker AI está rodando!"}