// src/App.jsx
import { useState, useEffect } from "react";
// Importa componentes necessários do Recharts
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

// Importa o arquivo CSS principal (que deve conter as diretivas Tailwind)
import "./App.css";

// Componente simples de Spinner para indicar carregamento
const LoadingSpinner = () => (
  <div className="flex justify-center items-center h-full py-10"> {/* Adicionado py-10 para dar espaço vertical */}
    {/* Usando classes Tailwind para estilizar o spinner */}
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-400"></div>
    <p className="ml-3 text-slate-400">Carregando...</p>
  </div>
);

// Defina o intervalo de polling em milissegundos (ex: 15 segundos)
const POLLING_INTERVAL_MS = 15000;

function App() {
  // Estados para armazenar os dados recebidos dos endpoints
  const [ultimaLeitura, setUltimaLeitura] = useState(null);
  const [leituras24h, setLeituras24h] = useState([]);
  // Estado para armazenar mensagens de erro globais
  const [erro, setErro] = useState(null);
  // Estados de loading separados para a carga inicial de cada seção
  const [isLoadingUltimaInicial, setIsLoadingUltimaInicial] = useState(true);
  const [isLoading24hInicial, setIsLoading24hInicial] = useState(true);

  // URLs dos seus endpoints no back-end Render
  // VERIFIQUE: se estes são os URLs e caminhos EXATOS que seu backend expõe
  const ULTIMA_LEITURA_URL = "https://projeto-caixa-dagua-api.onrender.com/ultima-leitura";
  const ULTIMAS_24H_URL = "https://projeto-caixa-dagua-api.onrender.com/ultimas-24h"; // Assumindo que retorna uma lista

  // Função auxiliar centralizada para buscar dados
  const fetchData = async (url, setData, setLoading, setError, isPolling = false) => {
    if (!isPolling && setLoading) {
      setLoading(true);
    }
    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Erro ${res.status}: ${res.statusText || "Falha ao buscar dados"}`);
      }
      const data = await res.json();
      setData(data);
      // Limpa o erro global *somente se* esta busca específica foi bem-sucedida
      // Se outra busca ainda tiver um erro ativo, isso pode ser um problema.
      // Uma abordagem mais robusta poderia limpar o erro apenas se *todas* as buscas estiverem ok,
      // ou ter erros separados por seção. Por enquanto, vamos manter assim.
      // Consideração: Se uma busca falha (e define erro) e a outra tem sucesso (e limpa erro),
      // o erro pode "piscar". Para este app, provavelmente ok.
       setError(null); // Limpa erro em caso de sucesso
    } catch (err) {
      console.error(`Erro ao buscar dados de ${url}:`, err);
      setError(err.message); // Define o erro global
    } finally {
      if (!isPolling && setLoading) {
        setLoading(false);
      }
    }
  };

  // ---- Efeito para Carga Inicial do Histórico (Últimas 24h) ----
  useEffect(() => {
    console.log("Buscando histórico inicial (24h)...");
    fetchData(
      ULTIMAS_24H_URL,
      (data) => {
        // VERIFIQUE: Nome do campo de data ('timestamp' ou 'created_on')
        const formattedData = Array.isArray(data)
          ? data
              .map((item) => ({
                ...item,
                distancia: typeof item.distancia === "number" ? item.distancia : null,
                timestamp: new Date(item.timestamp || item.created_on).getTime(), // Tenta 'timestamp', fallback para 'created_on'
              }))
              // Filtra itens onde a conversão de data falhou (resultando em NaN) ou distancia é null
              .filter(item => !isNaN(item.timestamp) && item.distancia !== null)
              .sort((a, b) => a.timestamp - b.timestamp) // Ordena por timestamp
          : [];
        setLeituras24h(formattedData);
      },
      setIsLoading24hInicial,
      setErro
    );
  }, []); // Executa só uma vez

  // ---- Efeito para Carga Inicial E Polling da Última Leitura ----
  useEffect(() => {
    // 1. Busca Inicial
    console.log("Buscando última leitura inicial...");
    fetchData(
      ULTIMA_LEITURA_URL,
      (data) => {
        // VERIFIQUE: Nome do campo de data ('timestamp' ou 'created_on')
        setUltimaLeitura(data); // Assume que o backend retorna o objeto diretamente
      },
      setIsLoadingUltimaInicial,
      setErro
    );

    // 2. Configura o Polling
    console.log(`Configurando polling a cada ${POLLING_INTERVAL_MS / 1000} segundos...`);
    const intervalId = setInterval(() => {
      console.log("Polling: Buscando última leitura...");
      fetchData(
        ULTIMA_LEITURA_URL,
        (data) => {
           // VERIFIQUE: Nome do campo de data ('timestamp' ou 'created_on')
          setUltimaLeitura(data);
        },
        null, // Não usa setLoading no polling
        setErro,
        true // Indica que é polling
      );
    }, POLLING_INTERVAL_MS);

    // 3. Função de Limpeza
    return () => {
      console.log("Limpando intervalo de polling.");
      clearInterval(intervalId);
    };
  }, []); // Executa só uma vez

  // Funções auxiliares de formatação de data/hora
  const formatXAxis = (timestamp) =>
    typeof timestamp === "number" && !isNaN(timestamp)
      ? new Date(timestamp).toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "America/Recife",
        })
      : "N/A";

  const formatTooltipLabel = (timestamp) =>
    typeof timestamp === "number" && !isNaN(timestamp)
      ? new Date(timestamp).toLocaleString("pt-BR", {
          dateStyle: "short",
          timeStyle: "medium",
          timeZone: "America/Recife",
        })
      : "N/A";

  const formatUltimaLeituraTimestamp = (timestampString) => {
    if (!timestampString) return "Indisponível";
    try {
      const date = new Date(timestampString);
      if (isNaN(date.getTime())) {
        throw new Error("Data inválida recebida do backend");
      }
      return date.toLocaleString("pt-BR", {
        dateStyle: "full",
        timeStyle: "medium",
        timeZone: "America/Recife",
      });
    } catch (e) {
      console.error("Erro ao formatar timestamp da última leitura:", timestampString, e);
      return "Data inválida";
    }
  };

  // Renderização do componente (JSX)
  return (
    <div className="flex flex-col items-center justify-start min-h-screen p-4 sm:p-6 bg-slate-900 font-sans">
      <div className="w-full max-w-7xl"> {/* Aumentado max-w para acomodar melhor */}

        <h1 className="text-4xl sm:text-5xl font-extrabold text-center mb-2 tracking-tight bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent drop-shadow-sm">
          Monitoramento da Caixa d'Água
        </h1>

        <p dir="rtl" className="text-lg sm:text-xl text-center mb-8 sm:mb-10 text-slate-400 font-sans">
          مراقبة خزان المياه {/* Tradução: Monitoramento do tanque de água */}
        </p>

        {/* Mensagem de Erro Global */}
        {erro && (
          <div className="bg-red-900/80 border border-red-700 text-red-200 px-4 py-3 rounded-lg relative mb-6 text-center shadow" role="alert">
            <strong className="font-bold">Ocorreu um erro:</strong>{" "}
            <span className="block sm:inline ml-2">{erro}</span>
          </div>
        )}

        {/* Grid Principal */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">

          {/* Coluna da Esquerda: Última Leitura */}
          <div className="md:col-span-1 flex flex-col"> {/* Removido gap-8 daqui, pois só tem um item */}
            <div className="bg-slate-800 rounded-xl shadow-lg p-6 sm:p-8 transition-shadow hover:shadow-xl border border-slate-700 h-full flex flex-col"> {/* Adicionado h-full e flex flex-col */}
              <h2 className="text-xl sm:text-2xl font-semibold mb-5 text-slate-100 border-b pb-2 border-slate-700 flex-shrink-0"> {/* Adicionado flex-shrink-0 */}
                Última Leitura
              </h2>
              <div className="flex-grow flex items-center justify-center"> {/* Div para centralizar conteúdo */}
                {isLoadingUltimaInicial ? (
                  <LoadingSpinner />
                ) : ultimaLeitura ? (
                  <div className="text-slate-300 space-y-3 text-base sm:text-lg">
                    {/* VERIFIQUE: Nome do campo 'timestamp' ou 'created_on' no objeto ultimaLeitura */}
                    <p>
                      <span className="font-medium text-slate-100">ID:</span>{" "}
                      {ultimaLeitura.id || "N/A"}
                    </p>
                    <p>
                      <span className="font-medium text-slate-100">Nível:</span>{" "}
                      {typeof ultimaLeitura.distancia === "number"
                        ? `${ultimaLeitura.distancia.toFixed(1)} cm`
                        : "Indisponível"}
                    </p>
                    <p>
                      <span className="font-medium text-slate-100">Data:</span>{" "}
                      {formatUltimaLeituraTimestamp(ultimaLeitura.timestamp || ultimaLeitura.created_on)}
                    </p>
                  </div>
                ) : !erro ? ( // Só mostra "Nenhuma leitura" se não houver erro
                  <p className="text-slate-500 text-center">Nenhuma leitura disponível.</p>
                ): null } {/* Se houver erro, a mensagem de erro global já é mostrada */}
              </div>
            </div>
          </div>

          {/* Coluna da Direita: Gráfico Histórico */}
          <div className="md:col-span-2">
            <div className="bg-slate-800 rounded-xl shadow-lg p-6 sm:p-8 transition-shadow hover:shadow-xl border border-slate-700 h-full flex flex-col">
              <h2 className="text-xl sm:text-2xl font-semibold mb-5 text-slate-100 border-b pb-2 border-slate-700 flex-shrink-0">
                Histórico - Últimas 24 Horas
              </h2>
              <div className="flex-grow min-h-[300px] sm:min-h-[400px]"> {/* Garante altura mínima para o gráfico */}
                {isLoading24hInicial ? (
                  <LoadingSpinner />
                ) : leituras24h.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={leituras24h}
                      margin={{
                        top: 5,
                        right: 20, // Aumentado para evitar corte de label
                        left: 0,  // Ajustado para texto da YAxis
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#475569" /> {/* Cor do grid slate-600 */}
                      <XAxis
                        dataKey="timestamp"
                        tickFormatter={formatXAxis}
                        stroke="#94a3b8" // Cor do eixo e ticks slate-400
                        tick={{ fontSize: 12 }}
                        // interval="preserveStartEnd" // Pode ajudar a garantir o primeiro/último tick
                        // minTickGap={50} // Aumenta espaço entre ticks se ficarem muito juntos
                      />
                      <YAxis
                        dataKey="distancia"
                        stroke="#94a3b8" // Cor do eixo e ticks slate-400
                        tick={{ fontSize: 12 }}
                        domain={['dataMin - 5', 'dataMax + 5']} // Adiciona um pouco de padding
                        label={{ value: 'Nível (cm)', angle: -90, position: 'insideLeft', fill: '#cbd5e1', fontSize: 14, dx: -10 }} // Adiciona label no eixo Y
                        unit=" cm" // Adiciona unidade aos ticks
                      />
                      <Tooltip
                        labelFormatter={formatTooltipLabel}
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} // Estilo do tooltip (slate-800/700)
                        labelStyle={{ color: '#f1f5f9' }} // Cor do label (slate-100)
                        itemStyle={{ color: '#38bdf8' }} // Cor do item (sky-400)
                        formatter={(value) => [`${value.toFixed(1)} cm`, 'Nível']} // Formata valor e nome na tooltip
                      />
                      <Legend wrapperStyle={{ color: '#e2e8f0', paddingTop: '10px' }} /> {/* Cor da legenda (slate-200) */}
                      <Line
                        type="monotone"
                        dataKey="distancia"
                        name="Nível" // Nome que aparece na legenda e tooltip
                        stroke="#38bdf8" // Cor da linha (sky-400)
                        strokeWidth={2}
                        dot={false} // Oculta os pontos individuais
                        activeDot={{ r: 6, fill: '#0ea5e9', stroke: '#f8fafc', strokeWidth: 2 }} // Estilo do ponto ativo (hover)
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : !erro ? ( // Só mostra "Nenhum dado" se não houver erro
                  <div className="flex justify-center items-center h-full">
                      <p className="text-slate-500">Nenhum dado histórico disponível.</p>
                  </div>
                ) : null } {/* Se houver erro, a mensagem de erro global já é mostrada */}
              </div>
            </div>
          </div>

        </div> {/* Fim do Grid Principal */}

      </div> {/* Fim do Container Interno */}
    </div> /* Fim da DIV Principal */
  ); // Fim do return
} // Fim do componente App

export default App; // Exporta o componente