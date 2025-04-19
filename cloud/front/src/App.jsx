import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

// Componente LoadingSpinner
const LoadingSpinner = () => (
  <div className="flex justify-center items-center h-full">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-400"></div>
    <p className="ml-3 text-slate-400">Carregando...</p>
  </div>
);

const POLLING_INTERVAL_MS = 15000;

function App() {
  const [ultimaLeitura, setUltimaLeitura] = useState(null);
  const [leituras24h, setLeituras24h] = useState([]);
  const [erro, setErro] = useState(null);
  const [isLoadingUltimaInicial, setIsLoadingUltimaInicial] = useState(true);
  const [isLoading24hInicial, setIsLoading24hInicial] = useState(true);

  const fetchData = async (url, setData, setLoading, setError, isPolling = false) => {
    if (!isPolling && setLoading) {
      setLoading(true);
    }
    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Erro ${res.status}: ${res.statusText || 'Falha ao buscar dados'}`);
      }
      const data = await res.json();
      setData(data);
      setError(null);
    } catch (err) {
      console.error(`Erro ao buscar dados de ${url}:`, err);
      setError(err.message);
    } finally {
      if (!isPolling && setLoading) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    console.log("Buscando histórico inicial (24h)...");
    fetchData(
      "https://projeto-caixa-dagua-api.onrender.com/ultimas-24h",
      (data) => {
        const formattedData = data.map(item => ({
          ...item,
          distancia: typeof item.distancia === 'number' ? item.distancia : null,
          timestamp: new Date(item.timestamp).getTime()
        })).sort((a, b) => a.timestamp - b.timestamp);
        setLeituras24h(formattedData);
      },
      setIsLoading24hInicial,
      setErro
    );
  }, []);

  useEffect(() => {
    console.log("Buscando última leitura inicial...");
    fetchData(
      "https://projeto-caixa-dagua-api.onrender.com/ultima-leitura",
      setUltimaLeitura,
      setIsLoadingUltimaInicial,
      setErro
    );

    console.log(`Configurando polling a cada ${POLLING_INTERVAL_MS / 1000} segundos...`);
    const intervalId = setInterval(() => {
      console.log("Polling: Buscando última leitura...");
      fetchData(
        "https://projeto-caixa-dagua-api.onrender.com/ultima-leitura",
        setUltimaLeitura,
        null,
        setErro,
        true
      );
    }, POLLING_INTERVAL_MS);

    return () => {
      console.log("Limpando intervalo de polling.");
      clearInterval(intervalId);
    };
  }, []);

  // 🌎 FUSO HORÁRIO FIXO (Brasil)
  const TIMEZONE = 'America/Sao_Paulo';

  const formatXAxis = (timestamp) =>
    new Date(timestamp).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: TIMEZONE,
    });

  const formatTooltipLabel = (timestamp) =>
    new Date(timestamp).toLocaleString('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'medium',
      timeZone: TIMEZONE,
    });

  const formatUltimaLeituraTimestamp = (timestamp) => {
    if (!timestamp) return 'Indisponível';
    try {
      return new Date(timestamp).toLocaleString('pt-BR', {
        dateStyle: 'full',
        timeStyle: 'medium',
        timeZone: TIMEZONE,
      });
    } catch (e) {
      console.error("Erro ao formatar timestamp:", timestamp, e);
      return 'Data inválida';
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 bg-slate-900 font-sans">
      <div className="w-full max-w-6xl">
        <h1 className="text-5xl font-extrabold text-center mb-2 tracking-tight bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent drop-shadow-sm">
          Monitoramento da Caixa d'Água
        </h1>
        <p dir="rtl" className="text-xl text-center mb-10 text-slate-400 font-sans">
          مراقبة خزان المياه
        </p>

        {erro && (
          <div className="bg-red-900/80 border border-red-700 text-red-200 px-4 py-3 rounded-lg relative mb-6 text-center shadow" role="alert">
            <strong className="font-bold">Ocorreu um erro:</strong> <span className="block sm:inline ml-2">{erro}</span>
          </div>
        )}

        <div className="grid md:grid-cols-3 gap-8">
          <div className="md:col-span-1 flex flex-col gap-8">
            <div className="bg-slate-800 rounded-xl shadow-lg p-8 transition-shadow hover:shadow-xl border border-slate-700">
              <h2 className="text-2xl font-semibold mb-5 text-slate-100 border-b pb-2 border-slate-700">
                Última Leitura
              </h2>
              {isLoadingUltimaInicial ? (
                <LoadingSpinner />
              ) : ultimaLeitura ? (
                <div className="text-slate-300 space-y-3 text-lg">
                  <p><span className="font-medium text-slate-100">Nível:</span>{' '}{typeof ultimaLeitura.distancia === 'number' ? `${ultimaLeitura.distancia.toFixed(1)} cm` : 'Indisponível'}</p>
                  <p><span className="font-medium text-slate-100">Data:</span>{' '}{formatUltimaLeituraTimestamp(ultimaLeitura.timestamp)}</p>
                </div>
              ) : !erro ? (<p className="text-slate-500">Nenhuma leitura disponível.</p>) : null}
            </div>

            <div className="bg-slate-800 rounded-xl shadow-lg p-4 transition-shadow hover:shadow-xl border border-slate-700 flex items-center gap-4 flex-grow">
              <img
                src="/jvsv.jpg"
                alt="Foto de João Vitor"
                className="w-20 h-20 rounded-full object-cover border-2 border-sky-400 flex-shrink-0"
              />
              <div>
                <p className="text-sm text-slate-400">Desenvolvido por:</p>
                <p className="text-lg font-semibold text-slate-100">João Vítor Sgotti Veiga</p>
              </div>
            </div>
          </div>

          <div className="md:col-span-2 bg-slate-800 rounded-xl shadow-lg p-8 transition-shadow hover:shadow-xl border border-slate-700">
            <h2 className="text-2xl font-semibold mb-5 text-slate-100 border-b pb-2 border-slate-700">
              Histórico (Últimas 24h)
            </h2>
            {isLoading24hInicial ? (
              <div className="h-[300px] flex items-center justify-center"><LoadingSpinner /></div>
            ) : leituras24h.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={leituras24h} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="timestamp" tickFormatter={formatXAxis} stroke="#94a3b8" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                  <YAxis stroke="#94a3b8" tick={{ fontSize: 12, fill: '#94a3b8' }} domain={['dataMin - 5', 'dataMax + 5']} />
                  <Tooltip labelFormatter={formatTooltipLabel} contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.95)', borderColor: '#475569', borderRadius: '8px', boxShadow: '2px 2px 10px rgba(0,0,0,0.3)' }} itemStyle={{ color: '#818cf8' }} labelStyle={{ color: '#cbd5e1', fontWeight: 'bold' }} formatter={(value) => [`${typeof value === 'number' ? value.toFixed(1) : '?'} cm`, 'Distância']} />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} itemStyle={{ color: '#cbd5e1' }} />
                  <Line type="monotone" dataKey="distancia" name="Distância (cm)" stroke="#818cf8" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: '#818cf8', stroke: '#1e293b', strokeWidth: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : !erro ? (<div className="h-[300px] flex items-center justify-center"><p className="text-slate-500">Nenhum dado para exibir no gráfico.</p></div>) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
