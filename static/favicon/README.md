# Favicons - Natal de Luz e Prêmios

Esta pasta contém todos os favicons necessários para o site.

## 📁 Arquivos Incluídos

### Favicons Básicos
- `favicon.ico` - Favicon tradicional (16x16)
- `favicon-16x16.png` - Favicon pequeno
- `favicon-32x32.png` - Favicon médio

### Apple Touch Icons
- `apple-touch-icon.png` - Ícone para iOS (180x180)

### Android Icons
- `android-chrome-192x192.png` - Ícone Android pequeno
- `android-chrome-512x512.png` - Ícone Android grande

### Windows Tiles
- `mstile-150x150.png` - Ícone para Windows

### Safari
- `safari-pinned-tab.svg` - Ícone SVG para Safari

### Configuração
- `site.webmanifest` - Manifesto PWA
- `browserconfig.xml` - Configuração IE/Edge

## 🎨 Como Gerar os Favicons

### Opção 1: Usando o Script Python
```bash
# Instalar dependência
pip install Pillow

# Executar script
python generate_favicons.py
```

### Opção 2: Usando Ferramentas Online
1. Acesse: https://realfavicongenerator.net/
2. Faça upload da sua imagem (recomendado: 260x260px)
3. Configure as opções
4. Baixe e extraia os arquivos aqui

### Opção 3: Usando sua Logo
Se você tem uma logo da Liquida Teresina:
1. Redimensione para 512x512px
2. Use ferramentas online para gerar todos os tamanhos
3. Substitua os arquivos nesta pasta

## 🔧 Configuração no HTML

Os favicons já estão configurados no `base-bootstrap.html`:

```html
<!-- Favicons -->
<link rel="apple-touch-icon" sizes="180x180" href="{% static 'favicon/apple-touch-icon.png' %}">
<link rel="icon" type="image/png" sizes="32x32" href="{% static 'favicon/favicon-32x32.png' %}">
<link rel="icon" type="image/png" sizes="16x16" href="{% static 'favicon/favicon-16x16.png' %}">
<link rel="manifest" href="{% static 'favicon/site.webmanifest' %}">
<link rel="mask-icon" href="{% static 'favicon/safari-pinned-tab.svg' %}" color="#0d6efd">
<link rel="shortcut icon" href="{% static 'favicon/favicon.ico' %}">
<meta name="msapplication-TileColor" content="#0d6efd">
<meta name="msapplication-config" content="{% static 'favicon/browserconfig.xml' %}">
<meta name="theme-color" content="#0d6efd">
```

## 🎯 Cores Utilizadas

- **Cor principal**: #0d6efd (Azul Bootstrap)
- **Cor do texto**: #ffffff (Branco)
- **Cor de fundo**: #ffffff (Branco)

## 📱 Compatibilidade

- ✅ Chrome/Edge
- ✅ Firefox
- ✅ Safari
- ✅ iOS Safari
- ✅ Android Chrome
- ✅ Windows Tiles
- ✅ PWA Support

## 🚀 Próximos Passos

1. Execute o script Python para gerar os favicons
2. Teste em diferentes navegadores
3. Verifique se aparece na aba do navegador
4. Teste no mobile (ícone na tela inicial)
