import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// --- Constantes de Configuração ---
// Define a URL base da API para facilitar a modificação futura
const API_BASE_URL = "https://projeto-caixa-dagua-api.onrender.com"; 
// Define o intervalo de polling para a última leitura em milissegundos
const POLLING_INTERVAL_MS = 15000; // 15 segundos

// --- Componente LoadingSpinner (Mantido pela clareza) ---
// Componente simples para mostrar um indicador de carregamento
const LoadingSpinner = () => (
  <div className="loading-spinner"> {/* Classes simplificadas */}
    <div className="spinner-animation"></div> {/* Classes simplificadas */}
    <p>Calma lá, estou carregando...</p> {/* Texto mantido */}
  </div>
);

// --- Componente Principal da Aplicação (simplificado) ---
function App() {
  // --- Estados do Componente ---
  // Estado para armazenar a leitura mais recente
  const [ultimaLeitura, setUltimaLeitura] = useState(null);
  // Estado para armazenar o histórico de leituras (últimas 24h)
  const [leituras24h, setLeituras24h] = useState([]);
  // Estado para armazenar mensagens de erro
  const [erro, setErro] = useState(null);
  // Estados de loading separados para as cargas INICIAIS (para não sumir o gráfico/última leitura durante o polling)
  const [isLoadingUltimaInicial, setIsLoadingUltimaInicial] = useState(true);
  const [isLoading24hInicial, setIsLoading24hInicial] = useState(true);

  // --- Função Auxiliar para Buscar Dados ---
  // Função assíncrona para centralizar a lógica de busca de dados da API.
  const fetchData = async (url, setData, setLoading, setError, isPolling = false) => {
    // Define o estado de loading para TRUE APENAS se não for um polling e o setter de loading for fornecido
    if (!isPolling && setLoading) {
      setLoading(true);
    }
    // Nota: Não limpamos 'erro' globalmente aqui, um fetch bem-sucedido específico fará isso.

    try {
      // Realiza a chamada HTTP GET para a URL fornecida
      const res = await fetch(url);
      // Verifica se a resposta HTTP foi bem-sucedida (status 2xx)
      if (!res.ok) {
        // Se não foi sucesso, lança um erro com status e texto da resposta
        throw new Error(`Erro ${res.status}: ${res.statusText || 'Falha ao buscar dados'}`);
      }
      // Converte a resposta HTTP para JSON
      const data = await res.json();
      // Atualiza o estado dos dados com os dados recebidos
      setData(data);
      // Limpa o estado de erro global se a busca foi bem-sucedida
      setError(null);
    } catch (err) {
      // Captura e loga qualquer erro durante a busca
      console.error(`Erro ao buscar dados de ${url}:`, err);
      // Define o estado de erro global com a mensagem do erro
      setError(err.message);
    } finally {
      // Define o estado de loading para FALSE APENAS se não for um polling e o setter de loading for fornecido
      if (!isPolling && setLoading) {
        setLoading(false);
      }
    }
  };

  // ---- Efeito para Carga Inicial do Histórico (Últimas 24h) ----
  // Executa UMA VEZ após a renderização inicial do componente ([])
  useEffect(() => {
    console.log("Buscando histórico inicial (24h)...");

    // Chama a função fetchData para buscar o histórico
    fetchData(
      // CORRIGIDO: Usa a constante API_BASE_URL e o endpoint correto /leituras
      // Adiciona o parâmetro de query para buscar as últimas 24 horas
      `${API_BASE_URL}/leituras?periodo_horas=24`,
      (data) => {
        // Transforma os dados recebidos antes de salvar no estado:
        const formattedData = data
          .map(item => ({
            ...item,
            // CORRIGIDO: Usa item.created_on que é o nome da coluna no DB e API
            distancia: typeof item.distancia === 'number' ? item.distancia : null,
            // Converte o timestamp (string ISO 8601 de 'created_on') para um timestamp numérico (milissegundos)
            timestamp: new Date(item.created_on).getTime() // Usa created_on aqui
          }))
          // Ordena os dados por timestamp ascendente para o gráfico
          .sort((a, b) => a.timestamp - b.timestamp);

        setLeituras24h(formattedData); // Atualiza o estado do histórico
      },
      setIsLoading24hInicial, // Setter para o estado de loading inicial do histórico
      setErro // Setter para o estado de erro global
    );
  }, []); // Array de dependências vazio: executa apenas na montagem

  // ---- Efeito para Carga Inicial E Polling da Última Leitura ----
  // Executa UMA VEZ após a renderização inicial do componente ([])
  useEffect(() => {
    // 1. Busca Inicial da Última Leitura
    console.log("Buscando última leitura inicial...");
    fetchData(
      // CORRIGIDO: Usa a constante API_BASE_URL e o endpoint correto /leitura/ultima
      // REMOVIDO: O parâmetro 'limite=3' que não é esperado por este endpoint da API
      `${API_BASE_URL}/leitura/ultima`,
      setUltimaLeitura, // Setter para o estado da última leitura
      setIsLoadingUltimaInicial, // Setter para o estado de loading inicial da última leitura
      setErro // Setter para o estado de erro global
    );

    // 2. Configura o Polling para buscar a última leitura repetidamente
    console.log(`Configurando polling a cada ${POLLING_INTERVAL_MS / 1000} segundos...`);
    const intervalId = setInterval(() => {
      console.log("Polling: Buscando última leitura...");
      fetchData(
        // CORRIGIDO: Usa o endpoint correto para o polling
        `${API_BASE_URL}/leitura/ultima`,
        setUltimaLeitura, // Setter para o estado da última leitura
        null, // Não passa o setter de loading aqui, para não mostrar o spinner durante o polling
        setErro, // Setter para o estado de erro global
        true // Flag para indicar que é uma chamada de polling (usada na função fetchData)
      );
    }, POLLING_INTERVAL_MS); // Intervalo definido na constante

    // 3. Função de Limpeza: Executada quando o componente for desmontado
    // Essencial para limpar o intervalo e evitar vazamento de memória
    return () => {
      console.log("Limpando intervalo de polling.");
      clearInterval(intervalId); // Para o polling
    };

  }, []); // Array de dependências vazio: executa apenas na montagem

  // --- Funções de Formatação de Data/Hora ---
  // Funções para formatar os timestamps para exibição no gráfico e na interface.
  // Ajustadas para o fuso horário de Recife (America/Recife).

  // Formata o valor do eixo X do gráfico (hora:minuto)
  const formatXAxis = (timestamp) => {
     if (!timestamp) return ''; // Retorna string vazia para timestamps nulos/inválidos
     try {
        return new Date(timestamp).toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          timeZone: 'America/Recife'
        });
     } catch (e) {
        console.error("Erro ao formatar timestamp para XAxis:", timestamp, e);
        return 'Inválido';
     }
  };

  // Formata o rótulo do Tooltip do gráfico (data e hora completa)
  const formatTooltipLabel = (timestamp) => {
    if (!timestamp) return 'Data Indisponível';
    try {
      return new Date(timestamp).toLocaleString('pt-BR', {
        dateStyle: 'short', // ex: 23/04/2025
        timeStyle: 'medium', // ex: 14:30:00
        timeZone: 'America/Recife'
      });
    } catch (e) {
       console.error("Erro ao formatar timestamp para Tooltip:", timestamp, e);
       return 'Data Inválida';
    }
  };

  // Formata o timestamp da Última Leitura para exibição no card
  const formatUltimaLeituraTimestamp = (timestamp) => {
    // A API pode retornar um objeto vazio {} se não houver leituras,
    // então 'timestamp' pode ser undefined ou null.
    if (!timestamp) return 'Indisponível';
    try {
      // A API retorna o timestamp como string ISO 8601 na chave 'created_on'
      // Criamos um objeto Date a partir desta string e formatamos.
      // CORRIGIDO: Acessa created_on do objeto ultimaLeitura se ele existir
      // const date = new Date(ultimaLeitura.created_on); // Não, a função recebe o valor já extraído
      const date = new Date(timestamp);
       // Verifica se a data é válida
      if (isNaN(date.getTime())) {
        throw new Error("Data inválida após parse.");
      }
      return date.toLocaleString('pt-BR', {
        dateStyle: 'full',   // ex: terça-feira, 23 de abril de 2025
        timeStyle: 'medium', // ex: 14:30:00
        timeZone: 'America/Recife'
      });
    } catch (e) {
      console.error("Erro ao formatar timestamp da Última Leitura:", timestamp, e);
      return 'Data inválida';
    }
  }

  // --- Renderização da Interface ---
  return (
    // Container principal (classes simplificadas)
    <div className="app-container">
      {/* Título e Subtítulo (classes simplificadas, mantendo a estrutura) */}
      <h1 className="app-title">
        Monitoramento da Caixa d'Água
      </h1>
      <p className="app-subtitle">
        مراقبة خزان المياه {/* Subtítulo em árabe mantido */}
      </p>

      {/* Mensagem de Erro (classes simplificadas) */}
      {erro && (
        <div className="error-message">
          <strong>Ocorreu um erro:</strong> <span>{erro}</span>
        </div>
      )}

      {/* Layout principal em Grid (classes simplificadas) */}
      <div className="main-grid-layout">
        {/* Coluna Esquerda (classes simplificadas) */}
        <div className="left-column">
          {/* Card da Última Leitura (classes simplificadas) */}
          <div className="card">
            <h2 className="card-title">
              Última Leitura
            </h2>
            {/* Lógica de exibição condicional: Spinner, Dados, ou Mensagem */}
            {isLoadingUltimaInicial ? (
              // Mostra o spinner APENAS na carga inicial deste bloco
              <LoadingSpinner />
            ) : ultimaLeitura && typeof ultimaLeitura.distancia === 'number' ? (
               // Se não está carregando e há dados de última leitura com distância numérica
              <div className="data-display">
                <p><span>Nível:</span>{' '}{`${ultimaLeitura.distancia.toFixed(1)} cm`}</p>
                {/* CORRIGIDO: Passa ultimaLeitura.created_on para a função de formatação */}
                <p><span>Data:</span>{' '}{formatUltimaLeituraTimestamp(ultimaLeitura.created_on)}</p>
              </div>
             ) : !erro ? (
                // Se não está carregando, não há erro, e não há dados válidos
               <p>Nenhuma leitura disponível.</p>
             ) : (
                // Se há erro, não mostra mensagem de "nenhuma leitura", o erro global já aparece.
                // Poderia ser null ou <></>
                null
             )}
          </div>

          {/* Bloco de Perfil (classes simplificadas) */}
          <div className="profile-block">
             {/* Imagem mantida, classes simplificadas */}
             {/* Nota: a imagem /jvsv.jpg precisa existir na pasta 'public' do seu projeto Frontend */}
             <img
               src="/jvsv.jpg"
               alt="Foto de João Vitor"
               className="profile-image"
             />
             <div className="profile-text">
               <p>Desenvolvido por:</p>
               <p>João Vítor Sgotti Veiga</p>
             </div>
          </div>
        </div>

        {/* Coluna Direita: Gráfico (classes simplificadas) */}
        <div className="right-column card"> {/* Adicionado classe card para estilo */}
          <h2 className="card-title">
            Histórico (Últimas 24h)
          </h2>
          {/* Lógica de exibição condicional: Spinner, Gráfico, ou Mensagem */}
          {isLoading24hInicial ? (
            // Mostra o spinner APENAS na carga inicial deste bloco
            <div className="chart-loading-container"><LoadingSpinner /></div>
          ) : leituras24h.length > 0 ? (
             // Se não está carregando e há dados no histórico
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={leituras24h} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                {/* Grid, Eixos, Tooltip, Legenda (classes/estilos recharts mantidos) */}
                <CartesianGrid strokeDasharray="3 3" stroke="#ccc" /> {/* Stroke simplificado */}
                <XAxis dataKey="timestamp" tickFormatter={formatXAxis} stroke="#888" /> {/* Stroke simplificado */}
                <YAxis stroke="#888" domain={['dataMin - 5', 'dataMax + 5']} /> {/* Stroke simplificado */}
                {/* Tooltip e Legend styles mantidos para funcionalidade e legibilidade */}
                <Tooltip labelFormatter={formatTooltipLabel} contentStyle={{ backgroundColor: '#fff', borderColor: '#ccc' }} itemStyle={{ color: '#8884d8' }} labelStyle={{ fontWeight: 'bold' }} formatter={(value) => [`${typeof value === 'number' ? value.toFixed(1) : '?'} cm`, 'Distância']} />
                <Legend />
                {/* Linha do gráfico (stroke, dot styles mantidos para clareza visual) */}
                <Line type="monotone" dataKey="distancia" name="Distância (cm)" stroke="#8884d8" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: '#8884d8', stroke: '#fff', strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : !erro ? (
             // Se não está carregando, não há erro, e o histórico está vazio
             <div className="chart-empty-message-container"> {/* Classes simplificadas, CORRIGIDO o fechamento da div */}
                <p>Nenhum histórico disponível para as últimas 24h.</p>
             </div>
          ) : (
             // Se há erro, não mostra mensagem de "nenhum histórico", o erro global já aparece.
             null
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
