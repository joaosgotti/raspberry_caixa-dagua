import { useState, useEffect } from "react";
// Importa apenas os componentes necessários do Recharts
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
// URL base da API. Mude para a sua URL no Render ou local, se necessário.
const API_BASE_URL = "https://projeto-caixa-dagua-api.onrender.com"; // Altere este URL!
// Intervalo em milissegundos para buscar a última leitura novamente
const POLLING_INTERVAL_MS = 15000; // 15 segundos

// --- Componente de Loading Minimalista ---
// Apenas texto ou um spinner CSS simples
const LoadingSpinner = () => (
  <div className="loading">
    <p>Carregando...</p>
  </div>
);

// --- Componente Principal (Simplificado) ---
function App() {
  // --- Estados ---
  const [ultimaLeitura, setUltimaLeitura] = useState(null);
  const [leituras24h, setLeituras24h] = useState([]);
  const [erro, setErro] = useState(null);
  // Estados de loading para as cargas iniciais
  const [isLoadingUltimaInicial, setIsLoadingUltimaInicial] = useState(true);
  const [isLoading24hInicial, setIsLoading24hInicial] = useState(true);

  // --- Função para Buscar Dados ---
  // Função auxiliar para chamar a API, tratar resposta e erros.
  const fetchData = async (url, setData, setLoading, setError, isPolling = false) => {
    // Ativa loading apenas para cargas iniciais (se setLoading for fornecido)
    if (!isPolling && setLoading) {
      setLoading(true);
    }
    // Limpa erro específico desta busca (o erro global será sobrescrito se falhar)
    // setError(null); // Remover esta linha, o catch já setta o erro global

    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Erro HTTP ${res.status}: ${res.statusText || 'Falha na resposta'}`);
      }
      const data = await res.json();
      setData(data);
      // Limpa o erro global se esta busca for bem-sucedida
      setError(null);
    } catch (err) {
      console.error(`Erro ao buscar ${url}:`, err);
      // Define o erro global se ocorrer qualquer falha
      setError(`Falha ao buscar dados: ${err.message}`);
    } finally {
      // Desativa loading apenas para cargas iniciais (se setLoading for fornecido)
      if (!isPolling && setLoading) {
        setLoading(false);
      }
    }
  };

  // --- Efeito para Carga Inicial do Histórico (24h) ---
  // Busca o histórico UMA VEZ ao montar o componente.
  useEffect(() => {
    console.log("Buscando histórico inicial (24h)...");
    fetchData(
      `${API_BASE_URL}/leituras?periodo_horas=24`, // Endpoint corrigido para 24h
      (data) => {
        // Mapeia e formata os dados para o gráfico
        const formattedData = data
          .map(item => ({
            ...item,
            
            distancia: typeof item.distancia === 'number' ? item.distancia : null,
            created_on: new Date(item.created_on).getTime() 
          }))
          .sort((a, b) => a.created_on - b.created_on); // Ordena por tempo

        setLeituras24h(formattedData); // Salva no estado
      },
      setIsLoading24hInicial, // Atualiza loading inicial deste bloco
      setErro // Seta erro global
    );
  }, []); // Array vazio = executa apenas na montagem

  // --- Efeito para Carga Inicial da Última Leitura E Polling ---
  // Busca a última leitura inicialmente e configura o polling.
  useEffect(() => {
    // Busca inicial da última leitura
    console.log("Buscando última leitura inicial...");
    fetchData(
      `${API_BASE_URL}/leitura/ultima`, // Endpoint corrigido para última leitura
      setUltimaLeitura, // Salva no estado
      setIsLoadingUltimaInicial, // Atualiza loading inicial deste bloco
      setErro // Seta erro global
    );

    // Configura o intervalo de polling
    console.log(`Configurando polling a cada ${POLLING_INTERVAL_MS / 1000} segundos...`);
    const intervalId = setInterval(() => {
      console.log("Polling: Buscando última leitura...");
      fetchData(
        `${API_BASE_URL}/leitura/ultima`, // Endpoint para polling
        setUltimaLeitura,
        null, // Não atualiza loading durante polling
        setErro,
        true // Indica que é polling
      );
    }, POLLING_INTERVAL_MS);

    // Função de limpeza: executada ao desmontar o componente
    return () => {
      console.log("Limpando intervalo de polling.");
      clearInterval(intervalId); // Interrompe o polling
    };

  }, []); // Array vazio = configura apenas na montagem

  // --- Funções de Formatação de Data/Hora (Mantidas) ---
  // Formatam created_on para exibição, ajustando para fuso horário de Recife.
  const formatXAxis = (created_on) => {
     if (!created_on) return '';
     try {
        return new Date(created_on).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Recife' });
     } catch (e) { return 'Inválido'; }
  };

  const formatTooltipLabel = (created_on) => {
    if (!created_on) return 'Data Indisponível';
    try {
      return new Date(created_on).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium', timeZone: 'America/Recife' });
    } catch (e) { return 'Data Inválida'; }
  };

  const formatUltimaLeituraCreatedOn = (created_on) => {
    if (!created_on) return 'Indisponível';
    try {
      // Usa o created_on recebido (que será ultimaLeitura.created_on)
      const date = new Date(created_on);
      if (isNaN(date.getTime())) throw new Error("Data inválida.");
      return date.toLocaleString('pt-BR', { dateStyle: 'full', timeStyle: 'medium', timeZone: 'America/Recife' });
    } catch (e) {
      console.error("Erro ao formatar created_on:", created_on, e);
      return 'Data inválida';
    }
  }

  // --- Renderização (HTML/JSX Simplificado) ---
  return (
    <div className="container"> {/* Classe CSS simples */}
      <h1 className="title">Monitoramento da Caixa d'Água</h1> {/* Classe CSS simples */}
      <p className="subtitle">مراقبة خزان المياه</p> {/* Classe CSS simples */}

      {/* Exibe mensagem de erro se houver */}
      {erro && <div className="error-message">{erro}</div>} {/* Classe CSS simples */}

      {/* Layout básico flexível ou em blocos */}
      <div className="content-area"> {/* Classe CSS simples */}

        {/* Seção Última Leitura */}
        <div className="card"> {/* Classe CSS simples */}
          <h2 className="card-title">Última Leitura</h2> {/* Classe CSS simples */}
          {isLoadingUltimaInicial ? (
            <LoadingSpinner />
          ) : ultimaLeitura && typeof ultimaLeitura.distancia === 'number' ? (
             // Se não está carregando e há dados de última leitura com distância numérica
            <div className="data-item"> {/* Classe CSS simples */}
              <p>Nível: {ultimaLeitura.distancia.toFixed(1)} cm</p>
              {/* Passa ultimaLeitura.created_on para a função de formatação */}
              <p>Data: {formatUltimaLeituraCreatedOn(ultimaLeitura.created_on)}</p>
            </div>
          ) : !erro ? (
            <p>Nenhuma leitura disponível.</p>
          ) : null}
        </div>

        {/* Seção Histórico (Gráfico) */}
        <div className="card chart-card"> {/* Classes CSS simples */}
           <h2 className="card-title">Histórico (Últimas 24h)</h2> {/* Classe CSS simples */}
           {isLoading24hInicial ? (
             // Mostra spinner na carga inicial do histórico
             <div className="chart-loading-container"><LoadingSpinner /></div>
           ) : leituras24h.length > 0 ? (
             // Se não está carregando e há dados no histórico, mostra o gráfico
             <ResponsiveContainer width="100%" height={300}>
               <LineChart data={leituras24h} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                 <CartesianGrid strokeDasharray="3 3" stroke="#eee" /> {/* Stroke simplificado */}
                 <XAxis dataKey="created_on" tickFormatter={formatXAxis} stroke="#888" /> {/* Stroke simplificado */}
                 <YAxis stroke="#888" domain={['dataMin - 5', 'dataMax + 5']} /> {/* Stroke simplificado */}
                 {/* Tooltip e Legend mantidos pela funcionalidade */}
                 <Tooltip labelFormatter={formatTooltipLabel} />
                 <Legend />
                 {/* Linha do gráfico */}
                 <Line type="monotone" dataKey="distancia" name="Distância (cm)" stroke="#8884d8" strokeWidth={2} dot={false} />
               </LineChart>
             </ResponsiveContainer>
           ) : !erro ? (
             // Se não está carregando, não há erro e o histórico está vazio
             <div className="chart-empty-message-container">
               <p>Nenhum histórico disponível para as últimas 24h.</p>
             </div>
           ) : null}
        </div>

        {/* Bloco de Perfil (Opcional, mantido simplificado) */}
        <div className="profile-block"> {/* Classe CSS simples */}
          {/* Nota: a imagem /jvsv.jpg precisa estar na pasta 'public' */}
          <img src="/jvsv.jpg" alt="Foto de João Vitor" className="profile-image" /> {/* Classe CSS simples */}
          <div className="profile-text"> {/* Classe CSS simples */}
            <p>Desenvolvido por:</p>
            <p>João Vítor Sgotti Veiga</p>
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;