# Guia de Contribuição - NeuroDrive

Obrigado por querer contribuir com o NeuroDrive! Este documento fornece diretrizes e instruções para contribuir com nosso projeto.

## 📋 Índice

- [Como Começar](#como-começar)
- - [Reportando Bugs](#reportando-bugs)
  - - [Sugerindo Melhorias](#sugerindo-melhorias)
    - - [Pull Requests](#pull-requests)
      - - [Padrões de Código](#padrões-de-código)
        - - [Commits](#commits)
          - - [Testes](#testes)
           
            - ## Como Começar
           
            - ### 1. Fork o Repositório
           
            - Clique no botão "Fork" no topo da página do repositório.
           
            - ### 2. Clone Seu Fork
           
            - ```bash
              git clone https://github.com/seu-usuario/neurodrive.git
              cd neurodrive
              ```

              ### 3. Crie um Ambiente Virtual

              ```bash
              python -m venv venv
              source venv/bin/activate  # No Windows: venv\Scripts\activate
              ```

              ### 4. Instale as Dependências

              ```bash
              pip install -r requirements.txt
              ```

              ### 5. Crie uma Branch para Sua Feature

              ```bash
              git checkout -b feature/sua-feature-nome
              ```

              ## 🐛 Reportando Bugs

              Antes de criar um relatório de bug, verifique se o problema já não foi reportado.

              ### Como Enviar Um Bom Relatório de Bug

              Os bugs são rastreados como [GitHub Issues](https://github.com/eduardo-a-xavier/neurodrive/issues).

              Forneça as seguintes informações:

              - **Título descritivo**: Uma descrição clara do bug
              - - **Descrição exata**: Como reproduzir o problema (passo a passo)
                - - **Comportamento esperado**: O que deveria acontecer
                  - - **Comportamento atual**: O que está acontecendo
                    - - **Screenshots/Logs**: Se aplicável
                      - - **Ambiente**: Sistema operacional, versão Python, etc.
                       
                        - **Exemplo:**
                       
                        - ```
                          Título: Video feed não inicia na primeira tentativa

                          Passos para reproduzir:
                          1. Iniciar web_server.py
                          2. Acessar localhost:5000
                          3. Clicar em "Start Stream"

                          Esperado: Vídeo começa a transmitir
                          Atual: Erro "Camera not found"

                          Ambiente: Windows 10, Python 3.8.10
                          ```

                          ## 💡 Sugerindo Melhorias

                          Sugestões de melhorias também são rastreadas como [GitHub Issues](https://github.com/eduardo-a-xavier/neurodrive/issues).

                          Ao criar uma sugestão, inclua:

                          - **Descrição clara**: O que você quer que seja adicionado
                          - - **Justificativa**: Por que seria útil
                            - - **Exemplos**: Referências ou exemplos se possível
                              - - **Contexto adicional**: Qualquer outra informação relevante
                               
                                - ## 🔀 Pull Requests
                               
                                - ### Antes de Começar
                               
                                - 1. Verifique se existe uma issue associada
                                  2. 2. Leia toda a documentação relevante
                                     3. 3. Acompanhe os padrões de código (veja abaixo)
                                       
                                        4. ### Processo
                                       
                                        5. 1. **Faça seu commit** em sua branch
                                           2. 2. **Empurre para seu fork** (`git push origin feature/sua-feature`)
                                              3. 3. **Abra um Pull Request** no repositório original
                                                 4. 4. **Preencha o template** do PR completamente
                                                    5. 5. **Aguarde a revisão** dos mantenedores
                                                      
                                                       6. ### Template de Pull Request
                                                      
                                                       7. ```
                                                          ## Descrição
                                                          Breve descrição do que este PR faz.

                                                          ## Tipo de Mudança
                                                          - [ ] Bug fix
                                                          - [ ] Nova feature
                                                          - [ ] Melhoria de código
                                                          - [ ] Documentação
                                                          - [ ] Outra (especifique)

                                                          ## Relacionado a Issue
                                                          Fecha #123 (se aplicável)

                                                          ## Testes Realizados
                                                          Descreva os testes que você realizou.

                                                          ## Checklist
                                                          - [ ] Meu código segue os padrões de estilo do projeto
                                                          - [ ] Eu realizei uma auto-revisão do meu próprio código
                                                          - [ ] Eu comentei o código, especialmente em partes complexas
                                                          - [ ] Eu atualizei a documentação relevante
                                                          - [ ] Minhas mudanças não geram novos warnings
                                                          - [ ] Eu adicionei testes que provam meu fix/feature
                                                          ```

                                                          ## 📐 Padrões de Código

                                                          ### Python (PEP 8)

                                                          - Use 4 espaços para indentação
                                                          - - Máximo 88 caracteres por linha (Black formatter)
                                                            - - Nomes descritivos para variáveis e funções
                                                              - - Use type hints quando possível
                                                               
                                                                - ```python
                                                                  def detect_lanes(image: np.ndarray, threshold: int = 100) -> np.ndarray:
                                                                      """Detect lane markings in an image.

                                                                      Args:
                                                                          image: Input image as numpy array
                                                                          threshold: Detection threshold value

                                                                      Returns:
                                                                          Processed image with detected lanes
                                                                      """
                                                                      # Implementation here
                                                                      pass
                                                                      ```

                                                                  ### JavaScript/Web

                                                                  - Use 2 espaços para indentação
                                                                  - Use `const` por padrão, `let` quando necessário
                                                                  - Nomes descritivos em camelCase
                                                                  - Adicione comentários em código complexo

                                                                  ```javascript
                                                                  const processFrameData = (frameData) => {
                                                                    // Process telemetry data
                                                                    return frameData;
                                                                  };
                                                                  ```

                                                                  ### Docstrings

                                                                  Sempre inclua docstrings em funções:

                                                                  ```python
                                                                  def your_function(param1, param2):
                                                                      """
                                                                      Brief description of what the function does.

                                                                      Args:
                                                                          param1: Description of param1
                                                                          param2: Description of param2

                                                                      Returns:
                                                                          Description of return value

                                                                      Raises:
                                                                          ValueError: When something is invalid
                                                                      """
                                                                  ```

                                                                  ## 📝 Commits

                                                                  ### Formato de Mensagem

                                                                  Use o seguinte formato para mensagens de commit:

                                                                  ```
                                                                  <tipo>(<escopo>): <assunto>

                                                                  <corpo>

                                                                  <rodapé>
                                                                  ```

                                                                  ### Tipos

                                                                  - `feat`: Nova feature
                                                                  - - `fix`: Bug fix
                                                                    - - `docs`: Documentação
                                                                      - - `style`: Formatação, sem mudança de lógica
                                                                        - - `refactor`: Refatoração de código
                                                                          - - `test`: Adição ou atualização de testes
                                                                            - - `chore`: Atualizações de dependências, etc.
                                                                             
                                                                              - ### Exemplos
                                                                             
                                                                              - ```
                                                                                feat(pipeline): add real-time lane detection algorithm

                                                                                Implements the new deep learning model for lane detection
                                                                                with improved accuracy and speed.

                                                                                Closes #123
                                                                                ```

                                                                                ```
                                                                                fix(web): video stream timeout issue

                                                                                The video stream was timing out after 30 seconds.
                                                                                Increased timeout threshold and added reconnection logic.
                                                                                ```

                                                                                ## 🧪 Testes

                                                                                - Escreva testes para novas features
                                                                                - Rode os testes antes de fazer push
                                                                                - - Mantenha a cobertura de testes acima de 80%
                                                                                 
                                                                                  - ```bash
                                                                                    # Rodar testes
                                                                                    python -m pytest

                                                                                    # Com cobertura
                                                                                    python -m pytest --cov=neurodrive
                                                                                    ```

                                                                                    ## 📞 Dúvidas?

                                                                                    - Abra uma [Discussion](https://github.com/eduardo-a-xavier/neurodrive/discussions)
                                                                                    - - Verifique as [Issues](https://github.com/eduardo-a-xavier/neurodrive/issues)
                                                                                      - - Leia a [Documentação](https://github.com/eduardo-a-xavier/neurodrive/blob/main/README.md)
                                                                                       
                                                                                        - ## ⚖️ Código de Conduta
                                                                                       
                                                                                        - ### Nossa Promessa
                                                                                       
                                                                                        - No interesse de promover um ambiente aberto e acolhedor, nós, como colaboradores e mantenedores, nos comprometemos a fazer da participação em nosso projeto e comunidade uma experiência livre de assédio para todos.
                                                                                       
                                                                                        - ### Nossos Padrões
                                                                                       
                                                                                        - Exemplos de comportamento que contribuem para criar um ambiente positivo incluem:
                                                                                       
                                                                                        - - Usar linguagem acolhedora e inclusiva
                                                                                          - - Ser respeitoso com pontos de vista e experiências diferentes
                                                                                            - - Aceitar críticas construtivas graciosamente
                                                                                              - - Focar no que é melhor para a comunidade
                                                                                                - - Mostrar empatia com outros membros da comunidade
                                                                                                 
                                                                                                  - ### Aplicação
                                                                                                 
                                                                                                  - Instâncias de comportamento abusivo, de assédio ou inaceitável podem ser reportadas entrando em contato com a equipe do projeto. Todas as reclamações serão revisadas e investigadas.
                                                                                                 
                                                                                                  - ---

                                                                                                  **Obrigado por contribuir com o NeuroDrive! 🎉**
