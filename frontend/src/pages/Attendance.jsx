import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { faceAPI } from '../services/api';

function Attendance() {
  const { t } = useTranslation();

  // 오늘 날짜
  const todayStr = new Date().toISOString().split('T')[0];

  // 상태
  const [selectedDate, setSelectedDate] = useState(todayStr);
  const [records, setRecords] = useState([]);
  const [totalRegistered, setTotalRegistered] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statsMode, setStatsMode] = useState('7'); // '7', '30'
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState('daily'); // 'daily', 'stats'

  // 출석 기록 조회
  const fetchAttendance = useCallback(async () => {
    setLoading(true);
    try {
      const response = await faceAPI.getAttendanceByDate(selectedDate);
      setRecords(response.data.records || []);
    } catch (error) {
      console.error('출석 조회 실패:', error.message);
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  // 등록된 인원 수 조회
  const fetchRegisteredCount = useCallback(async () => {
    try {
      const response = await faceAPI.getFaces();
      setTotalRegistered(response.data.total || 0);
    } catch (error) {
      console.error('등록 인원 조회 실패:', error.message);
    }
  }, []);

  // 통계 조회
  const fetchStats = useCallback(async () => {
    try {
      const endDate = todayStr;
      const days = parseInt(statsMode);
      const start = new Date();
      start.setDate(start.getDate() - days + 1);
      const startDate = start.toISOString().split('T')[0];

      const response = await faceAPI.getAttendanceStats(startDate, endDate);
      setStats(response.data);
    } catch (error) {
      console.error('통계 조회 실패:', error.message);
      setStats(null);
    }
  }, [statsMode, todayStr]);

  // 초기 로드
  useEffect(() => {
    fetchAttendance();
    fetchRegisteredCount();
  }, [fetchAttendance, fetchRegisteredCount]);

  // 통계 탭 전환 시 로드
  useEffect(() => {
    if (activeTab === 'stats') {
      fetchStats();
    }
  }, [activeTab, fetchStats]);

  // 오늘 날짜인 경우 자동 갱신 (10초 간격)
  useEffect(() => {
    if (selectedDate !== todayStr || activeTab !== 'daily') return;

    const intervalId = setInterval(fetchAttendance, 10000);
    return () => clearInterval(intervalId);
  }, [selectedDate, todayStr, activeTab, fetchAttendance]);

  // 날짜 이동
  const goToday = () => setSelectedDate(todayStr);
  const goPrevDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    setSelectedDate(d.toISOString().split('T')[0]);
  };
  const goNextDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    if (d <= new Date()) {
      setSelectedDate(d.toISOString().split('T')[0]);
    }
  };

  const isToday = selectedDate === todayStr;

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* 헤더 */}
      <div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800">
          {t('attendance.title')}
        </h2>
        <p className="text-sm sm:text-base text-gray-600 mt-1 sm:mt-2">
          {t('attendance.subtitle')}
        </p>
      </div>

      {/* 탭 */}
      <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
        <button
          onClick={() => setActiveTab('daily')}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'daily'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          {t('attendance.tabs.daily')}
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'stats'
              ? 'bg-white text-blue-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          {t('attendance.tabs.stats')}
        </button>
      </div>

      {activeTab === 'daily' ? (
        <>
          {/* 오늘의 출석 요약 카드 */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">{t('attendance.summary.attended')}</p>
                  <p className="text-xl sm:text-3xl font-bold text-gray-800">{records.length}</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gray-400 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">{t('attendance.summary.registered')}</p>
                  <p className="text-xl sm:text-3xl font-bold text-gray-800">{totalRegistered}</p>
                </div>
              </div>
            </div>
          </div>

          {/* 날짜 선택 */}
          <div className="bg-white rounded-lg shadow-md p-3 sm:p-4">
            <div className="flex items-center justify-between">
              <button
                onClick={goPrevDay}
                className="p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              <div className="flex items-center space-x-3">
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  max={todayStr}
                  className="border rounded-lg px-3 py-2 text-sm sm:text-base text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {!isToday && (
                  <button
                    onClick={goToday}
                    className="px-3 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    {t('attendance.today')}
                  </button>
                )}
                {isToday && (
                  <span className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full font-medium">
                    {t('attendance.todayBadge')}
                  </span>
                )}
              </div>

              <button
                onClick={goNextDay}
                disabled={isToday}
                className={`p-2 rounded-lg transition-colors ${
                  isToday
                    ? 'text-gray-300 cursor-not-allowed'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>

          {/* 출석 기록 테이블 */}
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="p-3 sm:p-4 border-b">
              <h3 className="text-lg font-semibold text-gray-800">
                {t('attendance.records.title')}
              </h3>
            </div>

            {loading ? (
              <div className="p-8 text-center text-gray-500">
                {t('attendance.loading')}
              </div>
            ) : records.length === 0 ? (
              <div className="p-8 text-center">
                <svg className="w-16 h-16 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="text-gray-500">{t('attendance.records.empty')}</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        #
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {t('attendance.records.name')}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {t('attendance.records.time')}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        {t('attendance.records.confidence')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {records.map((record, index) => (
                      <tr key={record.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {index + 1}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm sm:text-base font-medium text-gray-800">
                            {record.name}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {record.time}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                            record.confidence >= 0.7
                              ? 'bg-green-100 text-green-700'
                              : record.confidence >= 0.5
                              ? 'bg-yellow-100 text-yellow-700'
                              : 'bg-red-100 text-red-700'
                          }`}>
                            {record.confidence
                              ? `${Math.round(record.confidence * 100)}%`
                              : '-'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
        /* 통계 탭 */
        <>
          {/* 기간 선택 */}
          <div className="flex space-x-2">
            {['7', '30'].map((days) => (
              <button
                key={days}
                onClick={() => setStatsMode(days)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statsMode === days
                    ? 'bg-blue-500 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100 shadow-sm'
                }`}
              >
                {t('attendance.stats.days', { count: days })}
              </button>
            ))}
          </div>

          {stats ? (
            <>
              {/* 통계 요약 */}
              <div className="grid grid-cols-2 gap-3 sm:gap-4">
                <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
                  <p className="text-xs sm:text-sm text-gray-600">{t('attendance.stats.totalDays')}</p>
                  <p className="text-2xl sm:text-3xl font-bold text-gray-800">{stats.total_days}</p>
                </div>
                <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
                  <p className="text-xs sm:text-sm text-gray-600">{t('attendance.stats.totalRecords')}</p>
                  <p className="text-2xl sm:text-3xl font-bold text-gray-800">{stats.total_records}</p>
                </div>
              </div>

              {/* 인물별 출석 현황 */}
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="p-3 sm:p-4 border-b">
                  <h3 className="text-lg font-semibold text-gray-800">
                    {t('attendance.stats.byPerson')}
                  </h3>
                </div>

                {stats.by_person.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    {t('attendance.stats.noData')}
                  </div>
                ) : (
                  <div className="divide-y divide-gray-200">
                    {stats.by_person.map((person, index) => {
                      const days = parseInt(statsMode);
                      const rate = Math.round((person.count / days) * 100);
                      return (
                        <div key={person.name} className="p-3 sm:p-4 flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <span className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-bold">
                              {index + 1}
                            </span>
                            <div>
                              <p className="font-medium text-gray-800">{person.name}</p>
                              <p className="text-xs text-gray-500">
                                {person.first_date} ~ {person.last_date}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-lg font-bold text-gray-800">
                              {person.count}{t('attendance.stats.timesUnit')}
                            </p>
                            <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                              <div
                                className="bg-blue-500 rounded-full h-2"
                                style={{ width: `${Math.min(rate, 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white rounded-lg shadow-md p-8 text-center text-gray-500">
              {t('attendance.loading')}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Attendance;
