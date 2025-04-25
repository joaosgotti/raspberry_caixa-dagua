// src/App.jsx
import { useState, useEffect } from 'react';
// Você pode remover as importações de logo.svg e App.css se não for usar.

function App() {
  // Estado para armazenar os dados recebidos do back-end
  const [statusData, setStatusData] = useState(null);
  // Estado para controlar se está carregando
  const [isLoading, setIsLoading] = useState(true);
  // Estado para armazenar erros
  const [error, setError] = useState(null);

  // URL do seu back-end.
  // Se estiver desenvolvendo localmente e o back-end rodar em localhost:8000,
  // e o front-end em localhost:5173 (padrão do Vite),
  // use a URL completa ou configure um proxy no Vite (mais avançado).
  // Para deploy, use a URL pública do seu back-end.
  const BACKEND_URL = '/status'; // Exemplo: 'https://seu-backend-aqui.render.com/status'

  // Função para buscar os dados do back-end
  const fetchStatus = async () => {
    setIsLoading(true);
    setError(null); // Limpa erros anteriores
    try {
      const response = await fetch(BACKEND_URL);

      if (!response.ok) {
        // Lança um erro se a resposta HTTP não for 2xx
        throw new Error(`Erro HTTP! Status: ${response.status}`);
      }

      const data = await response.json();
      setStatusData(data); // Atualiza o estado com os dados recebidos

    } catch (err) {
      console.error("Erro ao buscar status:", err);
      setError(err); // Armazena o erro no estado
    } finally {
      setIsLoading(false); // Finaliza o estado de carregamento
    }
  };

  // useEffect para buscar os dados quando o componente monta (apenas uma vez)
  useEffect(() => {
    fetchStatus();
  }, []); // Array de dependências vazio significa que executa apenas uma vez

  // Função para formatar a exibição dos dados (adapte conforme seu JSON)
  const renderStatus = () => {
      if (!statusData) return <p>Nenhum dado disponível.</p>;

      // Assumindo que seu JSON tem chaves como: nivel_agua, status_bomba, timestamp
      // Adapte conforme o JSON real do seu back-end
      return (
        <div>
          <p><strong>Nível da Água:</strong> {statusData.nivel_agua || 'N/A'}</p>
          <p><strong>Status da Bomba:</strong> {statusData.status_bomba || 'N/A'}</p>
          <p><strong>Última Atualização:</strong> {statusData.timestamp ? new Date(statusData.timestamp).toLocaleString() : 'N/A'}</p>
           <p><em>(Adapte a exibição acima conforme as chaves do seu JSON)</em></p>
        </div>
      );
  };

  return (
    <div>
      <h1>Status da Caixa D'água (React)</h1>

      <div style={{ marginTop: '20px', border: '1px solid #ccc', padding: '15px', minHeight: '80px' }}>
        {isLoading && <p>Carregando status...</p>}
        {error && <p style={{ color: 'red' }}>Erro: {error.message}</p>}
        {!isLoading && !error && renderStatus()}
      </div>

      <button onClick={fetchStatus} disabled={isLoading} style={{ marginTop: '10px', padding: '10px 20px', cursor: 'pointer' }}>
        {isLoading ? 'Atualizando...' : 'Atualizar Status'}
      </button>
    </div>
  );
}

export default App;