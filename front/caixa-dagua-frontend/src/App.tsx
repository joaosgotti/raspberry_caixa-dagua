import { useState, useEffect } from "react";
// Importa componentes do Recharts para o gráfico
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

// Importa o arquivo CSS principal onde o Tailwind está configurado (@tailwind directives)
// Este arquivo é onde o Tailwind gera todas as suas classes utilitárias
import './index.css'; // <<< Confirme se seu arquivo CSS principal se chama index.css

// Importa o arquivo CSS com estilos customizados que complementam o Tailwind (spinner, etc.)
// Este arquivo contém estilos para classes que não são do Tailwind, mas usamos no JSX (como .spinner)
import './App.css'; // <<< Importa o App.css com estilos customizados

// --- Constantes de Configuração ---
// ALtere esta URL para o endereço público da sua API no Render ou URL local!
// Certifique-se de que NÃO tem uma barra no final! Ex: "https://seu-backend-api.onrender.com"
const API_BASE_URL = "https://seu-backend-api.onrender.com"; // <<< MUDE ESTE URL PARA O DA SUA API!
// Intervalo em milissegundos para buscar a última leitura (15 segundos)
const POLLING_INTERVAL_MS = 15000;

// --- Componente de Loading com Estilo Tailwind e Spinner CSS ---
// Usa classes Tailwind para centralizar e cor, e classe customizada para o spinner animado
const LoadingSpinner = () => (
  // Flexbox para centralizar (coluna), margem superior, cor de texto cinza claro
  <div className="flex flex-col items-center justify-center mt-4 text-slate-400">
    {/* Elemento para a animação do spinner, usa a classe customizada "spinner" */}
    {/* A animação e forma são definidas no App.css para a classe .spinner */}
    <div className="spinner"></div> {/* Classe customizada para o spinner */}
    {/* Texto de carregamento com classes de margem e cor de texto */}
    <p className="mt-2 text-sm text-slate-400">Carregando...</p>
  </div>
);


// --- Componente Principal da Aplicação ---
function App() {
  // --- Estados ---
  const [ultimaLeitura, setUltimaLeitura] = useState(null); // Última leitura recebida (objeto ou null)
  const [leituras24h, setLeituras24h] = useState([]); // Histórico das últimas 24h (array de objetos)
  const [erro, setErro] = useState(null); // Mensagem de erro, se houver (string ou null)
  // Estados para mostrar "Carregando..." apenas nas cargas iniciais de cada seção
  const [isLoadingUltimaInicial, setIsLoadingUltimaInicial] = useState(true);
  const [isLoading24hInicial, setIsLoading24hInicial] = useState(true);

  // --- Função para Buscar Dados ---
  // Função auxiliar para chamar um URL da API, tratar resposta, erros e loadings.
  const fetchData = async (url, setData, setLoading, setError, isPolling = false) => {
    // Ativa o loading APENAS para a carga inicial associada a esta busca
    // Verifica se setLoading foi fornecido (não é fornecido para polling periódico)
    if (!isPolling && setLoading) {
      setLoading(true);
    }

    try {
      const res = await fetch(url); // Realiza a requisição HTTP para o URL fornecido
      if (!res.ok) {
        // Se a resposta não for bem-sucedida (status 4xx ou 5xx), lança um erro com o status e texto da resposta
        throw new Error(
          `Erro HTTP ${res.status}: ${res.statusText || "Falha na resposta da API"}`
        );
      }
      const data = await res.json(); // Converte a resposta para JSON
      setData(data); // Salva os dados no estado correspondente (ultimaLeitura ou leituras24h)
      setError(null); // Limpa qualquer erro anterior se esta busca foi bem-sucedida

      // --- Tratamento Específico para a Busca da Última Leitura ---
      // Se a busca for pela última leitura e a API retornar um objeto JSON vazio (sem dados),
      // define o estado `ultimaLeitura` como `null` para exibir a mensagem "Nenhuma leitura disponível".
      if (url.endsWith("/leitura/ultima") && data && typeof data === 'object' && Object.keys(data).length === 0) {
         console.log("API retornou objeto vazio para última leitura. Setando estado como null.");
         setUltimaLeitura(null); // Define o estado como null explicitamente
      }

    } catch (err) {
      console.error(`Erro ao buscar ${url}:`, err); // Loga o erro no console do navegador
      // Define a mensagem de erro global para ser exibida no topo da página
      setError(`Falha ao buscar dados: ${err.message}`);

      // --- Limpa Dados Correspondentes em Caso de Erro na Busca ---
      // Se ocorrer um erro durante a busca de dados, limpa os dados correspondentes no estado
      // para refletir que os dados não estão disponíveis ou estão inválidos.
      if (url.endsWith("/leitura/ultima")) {
         setUltimaLeitura(null); // Limpa a última leitura em caso de erro na busca dela
      }
       // Verifica se o URL inclui "/leituras?" para identificar a busca de histórico
      if (url.includes("/leituras?")) {
         setLeituras24h([]); // Limpa o array do histórico em caso de erro na busca dele
      }

    } finally {
      // Desativa o loading APENAS para a carga inicial associada a esta busca
      // Este bloco sempre executa após try/catch, garantindo que o loading inicial finalize.
      if (!isPolling && setLoading) {
        setLoading(false);
      }
    }
  };

  // --- Efeito para Carga Inicial do Histórico (Últimas 24h) ---
  // Executa UMA VEZ ao montar o componente para buscar o histórico de dados.
  useEffect(() => {
    console.log("Buscando histórico inicial (24h)..."); // Log para debug
    fetchData(
      `${API_BASE_URL}/leituras?periodo_horas=24`, // URL para buscar 24h de dados da API
      (data) => {
        // Callback para processar os dados recebidos do histórico
        // Verifica se 'data' é um array antes de processar (resposta da API deve ser um array)
        if (!Array.isArray(data)) {
             console.error("Dados do histórico não são um array:", data); // Loga erro se o formato não for array
             setLeituras24h([]); // Define como array vazio em caso de formato inesperado
             return; // Sai da função de callback para não tentar mapear algo que não é array
        }

        // Formata os dados para o gráfico: converte timestamp e garante valor numérico para distância
        const formattedData = data
          .map((item) => ({
            ...item, // Copia todas as outras propriedades do item original (como id, etc.)
            // A API retorna o timestamp na chave 'created_on'
            distancia: typeof item.distancia === "number" ? item.distancia : null, // Garante que distancia é número ou null
            // Converte a string ISO 8601 de 'created_on' para um timestamp numérico (milissegundos desde a Época) para o gráfico
            created_on: item.created_on ? new Date(item.created_on).getTime() : null // Converte created_on para numérico, com checagem se 'created_on' existe no item
          }))
          // Filtra itens que não puderam ser formatados corretamente (timestamp ou distancia inválidos/nulos)
          .filter(item => item.created_on !== null && typeof item.distancia === 'number')
          // Ordena os dados por tempo (created_on numérico) em ordem ascendente (do mais antigo para o mais novo)
          .sort((a, b) => a.created_on - b.created_on);


        setLeituras24h(formattedData); // Atualiza o estado do histórico com os dados formatados e ordenados
      },
      setIsLoading24hInicial, // Setter de loading inicial específico para o histórico (desliga o spinner correspondente)
      setErro // Setter de erro global (para mostrar mensagem de erro no topo se a busca falhar)
    );
  }, []); // Array de dependências vazio: executa APENAS na montagem inicial do componente

  // --- Efeito para Carga Inicial da Última Leitura E Configuração do Polling ---
  // Executa UMA VEZ ao montar o componente para buscar a última leitura e iniciar o polling.
  useEffect(() => {
    // 1. Busca inicial da última leitura ao carregar a página
    console.log("Buscando última leitura inicial..."); // Log para debug
    fetchData(
      `${API_BASE_URL}/leitura/ultima`, // URL para a última leitura da API
      setUltimaLeitura, // Setter para a última leitura
      setIsLoadingUltimaInicial, // Setter de loading inicial específico para a última leitura
      setErro // Setter de erro global
    );

    // 2. Configura o intervalo para realizar polling periódico (busca a cada POLLING_INTERVAL_MS)
    console.log(`Configurando polling a cada ${POLLING_INTERVAL_MS / 1000} segundos...`); // Log para debug
    const intervalId = setInterval(() => {
      console.log("Polling: Buscando última leitura..."); // Log para debug de cada polling
      fetchData(
        `${API_BASE_URL}/leitura/ultima`, // URL para o polling (mesmo da busca inicial da última leitura)
        setUltimaLeitura, // Salva o novo dado da última leitura recebido (atualiza a interface)
        null, // Não forneça o setter de loading aqui, pois não queremos mostrar o spinner durante o polling
        setErro, // Setter de erro global (para mostrar mensagem de erro no topo se o polling falhar)
        true // Passa true para indicar para a função fetchData que esta é uma chamada de polling
      );
    }, POLLING_INTERVAL_MS); // Usa a constante do intervalo definido no topo

    // 3. Função de limpeza: Esta função é retornada pelo useEffect e será executada
    // quando o componente for desmontado (ex: sair da página ou componente for removido).
    // É ESSENCIAL para parar o intervalo de polling e evitar vazamentos de memória e chamadas de API desnecessárias.
    return () => {
      console.log("Limpando intervalo de polling."); // Log para debug da limpeza
      clearInterval(intervalId); // Interrompe o intervalo de polling agendado
    };

  }, []); // Array de dependências vazio: configura APENAS na montagem inicial do componente (e a função de retorno na desmontagem)

  // --- Funções de Formatação de Data/Hora ---
  // Formatam os timestamps (vindos da chave 'created_on' da API) para exibição.
  // O fuso horário 'America/Recife' é especificado para consistência com a localização do projeto.

  // Formata o valor no eixo X do gráfico (mostra apenas Hora:Minuto)
  const formatXAxis = (timestampNum) => {
     // Recebe o timestamp numérico (milissegundos desde a Época)
     if (!timestampNum) return ''; // Retorna vazio se o timestamp for nulo
     try {
        return new Date(timestampNum).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Recife' });
     } catch (e) {
        console.error("Erro ao formatar XAxis:", timestampNum, e);
        return 'Inválido'; // Retorna 'Inválido' em caso de erro de formatação
     }
  };

  // Formata o label que aparece no Tooltip do gráfico (mostra Data e Hora completa)
  const formatTooltipLabel = (timestampNum) => {
    // Recebe o timestamp numérico (milissegundos)
    if (!timestampNum) return 'Data Indisponível'; // Retorna mensagem se o timestamp for nulo
    try {
      return new Date(timestampNum).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium', timeZone: 'America/Recife' });
    } catch (e) {
       console.error("Erro ao formatar Tooltip:", timestampNum, e);
       return 'Data Inválida'; // Retorna 'Data Inválida' em caso de erro
    }
  };

  // Formata o timestamp para exibição no card da Última Leitura
  const formatUltimaLeituraCreatedOn = (isoString) => {
    // Recebe a string ISO 8601 diretamente do objeto ultimaLeitura.created_on
    if (!isoString) return 'Indisponível'; // Retorna mensagem se a string for nula/vazia
    try {
      const date = new Date(isoString); // Tenta converter a string ISO para objeto Date
      // Verifica se o objeto Date resultante é válido (evita "Invalid Date")
      if (isNaN(date.getTime())) throw new Error("Data inválida após parse.");
      return date.toLocaleString('pt-BR', { dateStyle: 'full', timeStyle: 'medium', timeZone: 'America/Recife' }); // Formata a data e hora completa
    } catch (e) {
      console.error("Erro ao formatar created_on:", isoString, e); // Loga erro no console
      return 'Data inválida'; // Retorna 'Data inválida' em caso de erro ou parse falho
    }
  }


  // --- Renderização da Interface (JSX com Classes Tailwind e Estrutura de Layout) ---
  return (
    // Container principal da página: fundo escuro, altura mínima, preenchimento, centralização flexbox
    <div className="bg-slate-900 min-h-screen p-6 flex flex-col items-center font-sans"> {/* font-sans para usar a fonte padrão sem ser serifada */}
      {/* Container interno para limitar a largura máxima do conteúdo e centralizá-lo */}
      <div className="w-full max-w-6xl"> {/* max-w-6xl define a largura máxima */}

        {/* Título principal: tamanho da fonte, negrito extra, centralizado, margem inferior, gradiente de cor, sombra */}
        <h1 className="text-5xl font-extrabold text-center mb-2 tracking-tight bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent drop-shadow-sm">
          Monitoramento da Caixa d'Água
        </h1>
         {/* Subtítulo: tamanho da fonte, cor cinza claro, centralizado, margem inferior, direção de texto da direita para esquerda */}
        <p dir="rtl" className="text-xl text-center mb-10 text-slate-400 font-sans"> {/* dir="rtl" para texto em árabe */}
          مراقبة خزان المياه {/* Subtítulo em árabe */}
        </p>

        {/* Área de Mensagem de Erro: fundo semi-transparente, borda, cor do texto, preenchimento, cantos arredondados, sombra, margem inferior */}
        {/* Exibição condicional: só aparece se a variável 'erro' for uma string não vazia */}
        {erro && typeof erro === 'string' && erro.length > 0 && (
          <div className="bg-red-900/80 border border-red-700 text-red-200 px-4 py-3 rounded-lg relative mb-6 text-center shadow" role="alert">
            <strong className="font-bold">Ocorreu um erro:</strong>
            <span className="block sm:inline ml-2">{erro}</span> {/* sm:inline para layout responsivo em telas pequenas */}
          </div>
        )}

        {/* Área de Conteúdo Principal: usa Grid layout responsivo */}
        {/* grid: ativa o display grid */}
        {/* grid-cols-1: em telas pequenas, 1 coluna (empilha os blocos verticalmente) */}
        {/* md:grid-cols-3: em telas médias (md) e maiores, divide em 3 colunas */}
        {/* gap-8: adiciona espaçamento MAIOR entre as células do grid (entre colunas e linhas) */}
        <div className="content-area grid grid-cols-1 md:grid-cols-3 gap-8"> {/* gap-8 conforme a imagem */}

          {/* --- Coluna da Esquerda (Ocupa 1/3 em telas médias+) --- */}
          {/* md:col-span-1: esta div ocupa 1 das 3 colunas a partir do breakpoint 'md' */}
          {/* flex flex-col: usa flexbox para organizar os itens INTERNOS (Última Leitura e Perfil) em coluna */}
          {/* gap-8: adiciona espaçamento MAIOR ENTRE os itens INTERNOS */}
          <div className="md:col-span-1 flex flex-col gap-8"> {/* gap-8 conforme a imagem */}

            {/* Bloco da Última Leitura */}
            {/* Fundo escuro, sombra, cantos arredondados, preenchimento, borda, transição/hover para sombra */}
            <div className="bg-slate-800 rounded-xl shadow-lg p-8 transition-shadow hover:shadow-xl border border-slate-700">
              {/* Título da seção: tamanho da fonte, seminegrito, margem inferior, borda inferior, cor */}
              <h2 className="text-2xl font-semibold mb-5 text-slate-100 border-b pb-2 border-slate-700">
                Última Leitura
              </h2>
              {/* Conteúdo da Última Leitura: exibe Loading, Dados, ou Mensagem de Vazio */}
              {isLoadingUltimaInicial ? (
                // Mostra spinner se estiver carregando inicialmente ESTA seção
                <LoadingSpinner />
              ) : ultimaLeitura && typeof ultimaLeitura.distancia === 'number' ? (
                // Se não está carregando E há dados válidos para a última leitura
                <div className="text-slate-300 space-y-3 text-lg"> {/* Cor do texto, espaçamento vertical, tamanho do texto */}
                  <p><span className="font-medium text-slate-100">Nível:</span>{' '}{ultimaLeitura.distancia.toFixed(1)} cm</p> {/* Exibe a distância formatada, com utilitários para destacar o valor */}
                  {/* Formata e exibe o timestamp (acessando ultimaLeitura.created_on) */}
                  <p><span className="font-medium text-slate-100">Data:</span>{' '}{formatUltimaLeituraCreatedOn(ultimaLeitura.created_on)}</p> {/* Destaca o label "Data:" */}
                </div>
              ) : !erro ? (
                // Se não está carregando, não há erro global, E não há dados válidos para última leitura
                // Mostra a mensagem de que não há leitura disponível
                <p className="text-slate-500">Nenhuma leitura disponível.</p>
              ) : (
                // Se há um erro global, não mostra nada aqui (a mensagem de erro já aparece no topo)
                null // Não renderiza nada neste caso
              )}
            </div>

            {/* Bloco de Perfil */}
            {/* Fundo escuro, sombra, cantos arredondados, preenchimento, borda, transição/hover para sombra, layout flex interno */}
             <div className="bg-slate-800 rounded-xl shadow-lg p-4 transition-shadow hover:shadow-xl border border-slate-700 flex items-center gap-4 flex-grow"> {/* flex-grow permite que este bloco ocupe o espaço restante na coluna esquerda, se necessário */}
                {/* Imagem do perfil com classes Tailwind para tamanho, forma, borda, cor e para não encolher */}
                {/* Nota: A imagem /jvsv.jpg precisa estar na pasta 'public' do seu projeto Frontend */}
               <img
                 src="/jvsv.jpg" // Caminho relativo à pasta public
                 alt="Foto de João Vitor"
                 className="w-20 h-20 rounded-full object-cover border-2 border-sky-400 flex-shrink-0" // w/h=20 (80px), border-2, border-sky-400 (cor da imagem)
               />
                {/* Texto do perfil com classes Tailwind para fonte, tamanho e cor */}
               <div className="flex-1"> {/* flex-1 permite que o texto ocupe o espaço restante */}
                  <p className="text-slate-400 text-sm">Desenvolvido por:</p> {/* Texto pequeno, cinza claro */}
                  <p className="text-slate-100 font-semibold text-lg">João Vítor Sgotti Veiga</p> {/* Nome em negrito, tamanho maior, cor branca */}
               </div>
            </div>

          </div> {/* Fim da Coluna da Esquerda */}

          {/* --- Coluna da Direita (Ocupa 2/3 em telas médias+) --- */}
          {/* md:col-span-2: esta div ocupa 2 das 3 colunas a partir do breakpoint 'md' */}
          {/* Fundo escuro, sombra, cantos arredondados, preenchimento, borda, transição/hover para sombra */}
          <div className="md:col-span-2 bg-slate-800 rounded-xl shadow-lg p-8 transition-shadow hover:shadow-xl border border-slate-700">
             {/* Título da seção: tamanho da fonte, seminegrito, margem inferior, borda inferior, cor */}
             <h2 className="text-2xl font-semibold mb-5 text-slate-100 border-b pb-2 border-slate-700">
               Histórico (Últimas 24h)
             </h2>
             {/* Área do Gráfico: exibe Loading, Gráfico, ou Mensagem de Vazio */}
             {isLoading24hInicial ? (
               // Mostra spinner se estiver carregando inicialmente ESTA seção
                // Container com altura definida para o spinner usando notação [] do Tailwind
               <div className="flex items-center justify-center h-[300px]"><LoadingSpinner /></div>
             ) : leituras24h.length > 0 ? (
               // Se não está carregando inicialmente E há dados no histórico, renderiza o gráfico
               // Container responsivo para o gráfico (React/Recharts), altura definida
               <ResponsiveContainer width="100%" height={300}>
                 {/* Componente do gráfico com margens e dados */}
                 <LineChart data={leituras24h} margin={{ top: 5, right: 20, left: 5, bottom: 5 }}>
                   {/* Linhas de grade no gráfico, cor cinza escuro via prop */}
                   <CartesianGrid strokeDasharray="3 3" stroke="#475569" /> {/* stroke com cor Slate 600 */}
                   {/* Eixo X (Tempo): dataKey 'created_on', formatação, cor e tamanho do texto via tick prop */}
                   <XAxis dataKey="created_on" tickFormatter={formatXAxis} stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} /> {/* stroke e tick fill com cor Slate 400 */}
                   {/* Eixo Y (Distância): cor e tamanho do texto via tick prop */}
                   <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} domain={['dataMin - 5', 'dataMax + 5']} /> {/* stroke e tick fill com cor Slate 400 */}
                   {/* Tooltip: aparece ao passar o mouse, formatação do label */}
                   {/* Estilo do tooltip usando valores hex ou RGBA consistentes com o tema escuro */}
                   <Tooltip
                       labelFormatter={formatTooltipLabel}
                       contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.95)', borderColor: '#475569', borderRadius: '8px', boxShadow: '2px 2px 10px rgba(0,0,0,0.3)' }} /* bg-slate-900/95, border-slate-600 */
                       itemStyle={{ color: '#818cf8' }} /* Cor da linha (Indigo 400 / Violet 400) para o texto do valor */
                       labelStyle={{ color: '#cbd5e1', fontWeight: 'bold' }} /* Cor do label (Slate 300) */
                   />
                   {/* Legenda do gráfico */}
                   <Legend wrapperStyle={{ paddingTop: '20px' }} itemStyle={{ color: '#cbd5e1' }} /> {/* Espaço acima, cor do texto da legenda (Slate 300) */}
                   {/* Linha do gráfico: dataKey 'distancia', nome "Distância (cm)", cor via prop */}
                   <Line type="monotone" dataKey="distancia" name="Distância (cm)" stroke="#818cf8" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: '#818cf8', stroke: '#1e293b', strokeWidth: 2 }} /> {/* stroke com cor Indigo 400/Violet 400, activeDot com cor e borda Slate 900 */}
                 </LineChart>
               </ResponsiveContainer>
             ) : !erro ? (
               // Se não está carregando inicialmente, não há erro global, E o histórico está vazio
               // Mostra a mensagem de que não há histórico disponível
                // Container para a mensagem, classe customizada para centralização e altura
               <div className="chart-empty-message-container"><p className="text-slate-500">Nenhum histórico disponível para as últimas 24h.</p></div> 
             ) : (
               // Se há um erro global, não mostra nada aqui.
               null // Não renderiza nada neste caso
             )}
           </div>

        </div> 
      </div> 
    </div> 
  );
}

// Exporta o componente para ser usado em main.jsx/index.js
export default App;