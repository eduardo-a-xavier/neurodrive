# NeuroDrive 🚗🧠

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Flask](https://img.shields.io/badge/Flask-Web-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-Active-brightgreen)

## Descrição

**NeuroDrive** é um pipeline avançado de visão computacional com inteligência artificial para detecção em tempo real de faixas de rodagem e coleta de telemetria. O projeto integra processamento de imagem com deep learning, oferecendo um dashboard PWA moderno para visualização de dados em tempo real.

## ✨ Características Principais

- **Detecção de Faixas em Tempo Real**: Algoritmos de visão computacional para identificar marcações de estrada
- - **Pipeline de IA**: Modelos de deep learning para análise e predição
  - - **Dashboard PWA**: Interface web responsiva com telemetria ao vivo
    - - **Sistema de Telemetria**: Coleta contínua de dados e métricas
      - - **Galeria e Equipe**: Visualização de histórico e informações de colaboradores
        - - **Streaming de Vídeo**: MJPEG para visualização em tempo real via Flask
         
          - ## 📁 Estrutura do Projeto
         
          - ```
            neurodrive/
            ├── README.md                          # Documentação principal
            ├── LICENSE                            # Licença MIT
            ├── CONTRIBUTING.md                    # Guia de contribuição
            ├── requirements.txt                   # Dependências Python
            ├── neurodrive_pipeline.py             # Pipeline de processamento
            ├── web_server.py                      # Servidor Flask com MJPEG
            ├── calibracao_neurodrive.json         # Arquivo de calibração
            ├── web/                               # Frontend PWA
            │   ├── index.html
            │   ├── style.css
            │   └── app.js
            └── .gitignore                         # Arquivos ignorados
            ```

            ## 🚀 Requisitos

            - Python 3.8 ou superior
            - - pip (gerenciador de pacotes Python)
              - - Câmera ou fonte de vídeo (opcional)
               
                - ### Dependências Principais
               
                - ```
                  opencv-python>=4.5.0       # Processamento de imagem
                  numpy>=1.19.0              # Computação numérica
                  flask>=2.0.0               # Framework web
                  tensorflow>=2.5.0          # Deep Learning (opcional)
                  scikit-learn>=0.24.0       # Machine Learning
                  ```

                  ## 📦 Instalação

                  ### 1. Clone o repositório

                  ```bash
                  git clone https://github.com/eduardo-a-xavier/neurodrive.git
                  cd neurodrive
                  ```

                  ### 2. Crie um ambiente virtual (recomendado)

                  ```bash
                  python -m venv venv
                  source venv/bin/activate  # No Windows: venv\Scripts\activate
                  ```

                  ### 3. Instale as dependências

                  ```bash
                  pip install -r requirements.txt
                  ```

                  ### 4. (Opcional) Configure o arquivo de calibração

                  Ajuste o arquivo `calibracao_neurodrive.json` com seus parâmetros específicos:

                  ```json
                  {
                    "camera_id": 0,
                    "frame_width": 1280,
                    "frame_height": 720,
                    "fps": 30
                  }
                  ```

                  ## 💻 Como Usar

                  ### Executar o Pipeline Principal

                  ```bash
                  python neurodrive_pipeline.py
                  ```

                  Este comando inicia o processamento de vídeo com detecção de faixas.

                  ### Iniciar o Servidor Web

                  ```bash
                  python web_server.py
                  ```

                  Acesse o dashboard em: `http://localhost:5000`

                  ### Modo de Desenvolvimento

                  Para desenvolvimento com hot-reload:

                  ```bash
                  export FLASK_ENV=development  # No Windows: set FLASK_ENV=development
                  python web_server.py
                  ```

                  ## 🏗️ Arquitetura

                  ```
                  Câmera/Vídeo Input
                      ↓
                  [neurodrive_pipeline.py]
                      ├─ Pré-processamento (redimensionamento, normalização)
                      ├─ Detecção de Faixas (CV)
                      ├─ Análise com IA (Deep Learning)
                      └─ Coleta de Telemetria
                      ↓
                  [web_server.py] - Flask com MJPEG
                      ├─ Streaming de vídeo
                      ├─ API REST para dados
                      └─ Dashboard PWA
                      ↓
                  Browser / PWA
                      ├─ Visualização em tempo real
                      ├─ Gráficos de telemetria
                      ├─ Galeria de quadros
                      └─ Informações da equipe
                  ```

                  ## 📊 API Endpoints

                  | Método | Endpoint | Descrição |
                  |--------|----------|-----------|
                  | GET | `/` | Dashboard principal |
                  | GET | `/video_feed` | Stream MJPEG |
                  | GET | `/api/telemetry` | Dados de telemetria em JSON |
                  | GET | `/api/stats` | Estatísticas gerais |
                  | POST | `/api/calibrate` | Reconfigurar calibração |

                  ## 🤝 Contribuindo

                  Contribuições são bem-vindas! Por favor, leia [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre nosso código de conduta e processo de submissão de pull requests.

                  ### Passos Rápidos para Contribuir

                  1. Fork o projeto
                  2. 2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
                     3. 3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
                        4. 4. Push para a branch (`git push origin feature/AmazingFeature`)
                           5. 5. Abra um Pull Request
                             
                              6. ## 📝 Licença
                             
                              7. Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.
                             
                              8. ## 👥 Autores
                             
                              9. - **Eduardo A. Xavier** - Desenvolvedor Principal - [GitHub](https://github.com/eduardo-a-xavier)
                                
                                 - ## 📞 Contato e Suporte
                                
                                 - - **Issues**: Use a aba [Issues](https://github.com/eduardo-a-xavier/neurodrive/issues) para reportar bugs
                                   - - **Discussions**: Abra uma [Discussion](https://github.com/eduardo-a-xavier/neurodrive/discussions) para dúvidas
                                     - - **Email**: Entre em contato via GitHub
                                      
                                       - ## 🙏 Agradecimentos
                                      
                                       - - Comunidade Open Source por bibliotecas incríveis
                                         - - Contribuidores que melhoram o projeto
                                           - - Inspiração em projetos similares de visão computacional
                                            
                                             - ---

                                             **Desenvolvido com ❤️ por [Eduardo A. Xavier](https://github.com/eduardo-a-xavier)**
