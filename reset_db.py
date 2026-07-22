import os
import sys

# Caminhos possíveis do banco de dados
db_paths = ["gym.db", "app/gym.db"]

print("🔍 Procurando bancos de dados antigos...")
for db_path in db_paths:
    if os.path.exists(db_path):
        print(f"🗑️ Deletando: {db_path}")
        os.remove(db_path)
    else:
        print(f"✅ Não encontrado: {db_path}")

print("\n🚀 Recriando o banco de dados com a nova estrutura...")
try:
    from app.database import engine, Base
    from app.models import Workout, Exercise  # Importa os modelos para garantir o registro
    
    # Isso força a criação das tabelas com TODAS as colunas novas
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados recriado com sucesso!")
    print("✅ Colunas novas (professor_profile, nickname, equipment, accessory, method) adicionadas.")
except Exception as e:
    print(f"❌ Erro ao recriar o banco: {e}")

print("\n🎉 Agora você pode iniciar o servidor com: uvicorn app.main:app --reload")