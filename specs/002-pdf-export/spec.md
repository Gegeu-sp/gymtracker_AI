# Feature Specification: Workout PDF Export & Print Formatting

**Feature Branch**: `002-pdf-export`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Adicione à página de resultados de treino existente uma funcionalidade que permita ao usuário exportar os cards de treino gerados para um PDF limpo e pronto para impressão. O PDF deve preservar a estrutura de 3 blocos (Aquecimento, Sessão Principal, Volta à Calma) e as observações de risco do treinador. Inclua um botão 'Baixar PDF' na parte inferior de cada card de treino no painel."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exportação de Card de Treino Individual para PDF (Priority: P1)

Como praticante de musculação ou personal trainer, quero clicar no botão "Baixar PDF" localizado na parte inferior do card de treino no painel/dashboard de resultados para gerar e baixar instantaneamente um documento PDF limpo, legível e formatado para impressão de uma sessão de treino específica.

**Why this priority**: É a funcionalidade central solicitada, permitindo transformar a prescrição digital em uma ficha de treino física/impressa de alta qualidade para uso prático na academia.

**Independent Test**: Pode ser testado acessando o painel de treinos, localizando qualquer card de treino gerado ou cadastrado, clicando no botão "Baixar PDF" no rodapé do card e verificando se o arquivo PDF correspondente é baixado no navegador.

**Acceptance Scenarios**:

1. **Given** um card de treino exibido no painel de resultados, **When** o usuário clica no botão "Baixar PDF" no rodapé do card, **Then** o sistema gera e inicia o download de um documento PDF nomeado como `Treino_[ID]_[Data].pdf` contendo as informações completas daquela sessão.
2. **Given** múltiplos cards de treinos na página de resultados, **When** o usuário clica em "Baixar PDF" no Card A, **Then** o PDF gerado contém estritamente os dados do Treino A, sem mesclar exercícios de outros cards.

---

### User Story 2 - Preservação dos 3 Blocos Metodológicos e Observações de Risco (Priority: P1)

Como atleta ou treinador, quero que o PDF exportado preserve estritamente a divisão em 3 blocos (Bloco 1: Aquecimento/Mobilidade, Bloco 2: Sessão Principal, Bloco 3: Volta à Calma/Recovery) e exiba com destaque no topo as observações de risco do treinador, garantindo a integridade fisiológica da prescrição.

**Why this priority**: Mantém o rigor metodológico e a segurança do praticante no papel impresso, garantindo que avisos sobre lesões e a sequência anatômica do treino não sejam perdidos.

**Independent Test**: Pode ser testado gerando o PDF de um treino que possua notas de risco e exercícios distribuídos nos 3 blocos, e inspecionando o documento gerado para confirmar a presença do box de alerta de risco no topo e os títulos/seções de cada bloco claramente demarcados.

**Acceptance Scenarios**:

1. **Given** um treino com notas do treinador (ex: "Alerta de Risco: Evitar amplitude máxima no supino devido a desconforto no ombro"), **When** o PDF é exportado, **Then** a observação aparece em um container de destaque (callout/badge) no topo da ficha de treino.
2. **Given** um treino composto pelos 3 blocos metodológicos, **When** o PDF é exportado, **Then** os exercícios são apresentados agrupados sob seus respectivos cabeçalhos de bloco (1. Aquecimento & Mobilidade, 2. Sessão Principal, 3. Volta à Calma & Recovery).

---

### User Story 3 - Layout Limpo e Otimizado para Impressão (Print-Friendly) (Priority: P2)

Como praticante de musculação, quero que o PDF gerado tenha um design limpo, contraste elevado e paleta eco-friendly (fundo claro sem grandes blocos escuros de tinta), além de colunas/espaços reservados para anotar a carga e repetições reais executadas a lápis/caneta.

**Why this priority**: Torna o PDF uma ferramenta de trabalho prática na academia, reduzindo o consumo de tinta na impressão e facilitando o acompanhamento tátil do treino.

**Independent Test**: Pode ser testado imprimindo ou visualizando o PDF em modo de pré-visualização de impressão, checando o fundo branco limpo, a tipografia nítida e a coluna para anotação tátil da execução real.

**Acceptance Scenarios**:

1. **Given** a geração do documento PDF, **When** visualizado ou impresso, **Then** o documento exibe fundo branco, linhas divisórias finas, tabelas organizadas e margens de página A4 perfeitamente enquadradas.
2. **Given** a tabela de exercícios no PDF, **When** apresentada ao usuário, **Then** inclui uma coluna dedicada ("Executado / Anotações") com linhas para preenchimento manual de Carga Real, Repetições e RPE.

---

### Edge Cases

- **Treino sem observações de risco (`notes` vazio)**: O box de alerta de risco é ocultado graciosamente no PDF, reaproveitando o espaço vertical de maneira fluida.
- **Treino extenso com múltiplos exercícios por bloco**: O layout do PDF aplica quebras de página limpas (page-break-inside: avoid) sem cortar tabelas de exercícios ou nomes pela metade.
- **Visualização em dispositivos móveis**: O botão "Baixar PDF" nos cards no painel é responsivo e touch-friendly, funcionando perfeitamente em telas de smartphones.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE adicionar um botão proeminente "Baixar PDF" na parte inferior / rodapé de cada card de treino exibido no painel de treinos (`app/static/dashboard.html` / `app/routers/workout.py`).
- **FR-002**: O PDF gerado DEVE estruturar o conteúdo em seções visuais claras separadas pelos 3 blocos metodológicos:
  - **Bloco 1**: Preparação & Ativação (Warm-up / Mobilidade)
  - **Bloco 2**: Sessão Principal (Main Session)
  - **Bloco 3**: Retorno à Homeostase (Cool-down / Recovery)
- **FR-003**: O PDF DEVE exibir no topo do documento (logo abaixo do cabeçalho com ID, data e origem) a seção **Observações de Risco & Notas do Treinador** (`notes`), em caixa de destaque visual com contraste.
- **FR-004**: O layout do PDF DEVE ser otimizado para impressão (Print-Friendly), utilizando fundo branco, textos em tons escuros de alta legibilidade, cabeçalhos de bloco em destaque sutil e tabela organizada por colunas.
- **FR-005**: A tabela de exercícios do PDF DEVE conter as seguintes colunas:
  1. **Exercício**: Nome do exercício e equipamento.
  2. **Prescrição**: Séries x Repetições.
  3. **Carga Prescrita**: Carga em kg.
  4. **Método / Cadência**: Método (ex: Drop-set, 3-0-1-0).
  5. **Registro Real (Anotação)**: Espaço em branco para anotação a caneta de Carga Real, Reps e RPE.
- **FR-006**: A geração do PDF DEVE ser client-side ou alimentada por serviço leve de PDF no backend, acionada diretamente pelo clique no botão sem recarregar a página do painel.

### Key Entities

- **Card de Treino (Workout Card Item)**: Entidade visual e de dados correspondente a uma sessão de treino cadastrada (`Workout`), com seus respectivos exercícios (`Exercise`), observações (`notes`) e metadados.
- **Documento Ficha de Treino PDF (Workout PDF Sheet)**: Artefato PDF formatado no padrão A4 pronto para visualização, salvamento e impressão física.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O clique no botão "Baixar PDF" em qualquer card gera e inicia o download do arquivo PDF em menos de 2.0 segundos.
- **SC-002**: 100% dos PDFs exportados mantêm a ordenação e classificação nos 3 blocos metodológicos e exibem as observações de risco quando existentes.
- **SC-003**: 100% dos PDFs exportados utilizam layout otimizado para impressão (fundo branco, zero desperdício de tinta, quebra de página ajustada para papel A4).
- **SC-004**: O layout do botão "Baixar PDF" é 100% integrado ao design visual existente do painel, garantindo responsividade em telas desktop e mobile.

## Assumptions

- O navegador do usuário possui suporte a download de arquivos PDF ou renderização de janelas de impressão / bibliotecas JavaScript de PDF (ex: `html2pdf.js` ou `jspdf` / `html2canvas` integrados via CDN ou biblioteca nativa no backend/frontend).
- A formatação A4 (210mm x 297mm) é o padrão de impressão adotado.
- Exercícios que contêm "Bloco 1" ou "Bloco 3" em seu nome ou método continuam sendo categorizados em seus blocos funcionais correspondentes.
