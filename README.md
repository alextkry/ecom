# Ecommerce - Sistema de Gerenciamento de Produtos

Sistema Django para gerenciamento de produtos com variantes dinâmicas e grupos de produtos.

## Características

- **Produtos com variantes dinâmicas**: Atributos como Cor, Comprimento, Número podem ser criados dinamicamente
- **Dependências implícitas**: As dependências entre atributos são inferidas automaticamente dos dados
- **Grupos de variantes**: Agrupe variantes por características similares para exibição
- **Navegação inteligente**: Sistema de "melhor correspondência" para navegar entre grupos/variantes
- **Edição em massa**: Interface estilo Excel com Handsontable para editar centenas de variantes
- **Histórico de preços**: Rastreamento automático de alterações de preços
- **API REST**: API completa com Django REST Framework + OpenAPI/Swagger

## Tecnologias

- Django 5.0
- PostgreSQL 16
- Redis 7
- Celery (tarefas assíncronas)
- Django REST Framework
- django-import-export (importação/exportação)
- Handsontable (edição em massa)
- django-imagekit (processamento de imagens)
- django-simple-history (histórico)

## Requisitos

- Docker e Docker Compose
- Python 3.12+ (se rodar localmente)

## Instalação com Docker

1. Clone o repositório:
```bash
git clone <repo-url>
cd ECOM_FROM_SCRATCH
```

2. Copie o arquivo de ambiente:
```bash
cp .env.example .env
```

3. Inicie os containers:
```bash
docker-compose up -d
```

4. Execute as migrações:
```bash
docker-compose exec web python manage.py migrate
```

5. Crie um superusuário:
```bash
docker-compose exec web python manage.py createsuperuser
```

6. Acesse:
- Admin: http://localhost:8000/admin/
- API Docs (Swagger): http://localhost:8000/api/docs/
- Edição em Massa: http://localhost:8000/catalog/bulk-edit/

## Estrutura do Projeto

```
├── apps/
│   └── catalog/
│       ├── api/                 # API REST
│       │   ├── serializers.py
│       │   ├── views.py
│       │   ├── filters.py
│       │   └── urls.py
│       ├── models/              # Modelos Django
│       │   ├── product.py       # Produto base
│       │   ├── attribute.py     # Tipos e opções de atributos
│       │   ├── variant.py       # Variantes (SKUs)
│       │   ├── variant_group.py # Grupos de variantes
│       │   └── price_history.py # Histórico de preços
│       ├── services/
│       │   └── variant_navigation.py  # Lógica de navegação
│       ├── admin.py             # Django Admin
│       ├── views.py             # Views (bulk edit)
│       └── signals.py           # Signals (histórico de preços)
├── config/                      # Configurações Django
├── templates/                   # Templates
└── docker-compose.yml
```

## Modelos de Dados

### Product (Produto)
Produto base que agrupa variantes. Ex: "Linha Modelo_X"

### AttributeType (Tipo de Atributo)
Tipos de atributos dinâmicos. Ex: "Cor", "Comprimento", "Número"

### AttributeOption (Opção de Atributo)
Valores possíveis para cada tipo. Ex: "branco", "230m", "5"

### Variant (Variante)
SKU individual com preço, estoque, imagens. Cada variante tem combinações de opções de atributos.

### VariantGroup (Grupo de Variantes)
Agrupamento de variantes para exibição. Ex: "Linha Modelo_X colorida (número 5)"

## API Endpoints

| Endpoint | Descrição |
|----------|-----------|
| GET /api/v1/products/ | Lista produtos |
| GET /api/v1/products/{slug}/ | Detalhe do produto com variantes |
| GET /api/v1/variants/ | Lista variantes |
| POST /api/v1/variants/bulk_update_prices/ | Atualização em massa de preços |
| GET /api/v1/variant-groups/ | Lista grupos |
| GET /api/v1/variant-groups/{id}/navigation/ | Dados de navegação |
| GET /api/v1/variant-groups/find_best_match/ | Encontrar grupo/variante |

## Navegação entre Variantes

O sistema infere dependências automaticamente. Por exemplo:
- Se Número 5 só existe com Comprimento 230m nos dados
- Ao selecionar Número 5, apenas Comprimento 230m será mostrado como disponível

Isso é calculado via queries, não precisa configurar manualmente.

## Edição em Massa

Acesse `/catalog/bulk-edit/` para uma interface estilo Excel onde você pode:
- Ver e editar múltiplas variantes
- Copiar/colar valores
- Usar autofill para preencher várias células
- Adicionar variantes a grupos
- Exportar/importar via admin (django-import-export)

## Licença

MIT
