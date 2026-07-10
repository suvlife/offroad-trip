/**
 * Cost calculation engine. Ported from backend/app/services/cost_service.py.
 */

import type { CostBreakdown } from "../types";

const FUEL_CONSUMPTION: Record<string, number> = {
  轿车: 7.0,
  中型轿车: 7.5,
  SUV: 9.0,
  越野车: 12.0,
  新能源: 15.0,
  混动: 6.0,
};
const FUEL_PRICE = 8.0;
const ELECTRICITY_PRICE = 1.0;
const TOLL_RATE = 0.45;
const HOTEL_PER_NIGHT = 350;
const MEAL_PER_PERSON = 80;
const SCENIC_TICKET = 80;

export function calculateSegmentCost(
  distanceKm: number,
  vehicleType = "SUV",
  hasToll = true,
  tollFromApi = 0
): { fuel_cost: number; toll_cost: number; total: number } {
  const consumption = FUEL_CONSUMPTION[vehicleType] ?? FUEL_CONSUMPTION.SUV;
  const fuelCost =
    vehicleType === "新能源"
      ? (distanceKm * consumption) / 100 * ELECTRICITY_PRICE
      : (distanceKm * consumption) / 100 * FUEL_PRICE;
  let tollCost = 0;
  if (tollFromApi > 0) tollCost = tollFromApi;
  else if (hasToll) tollCost = distanceKm * TOLL_RATE;
  return { fuel_cost: r1(fuelCost), toll_cost: r1(tollCost), total: r1(fuelCost + tollCost) };
}

export function calculateRouteCost(args: {
  totalDistance: number;
  days: number;
  adults: number;
  children: number;
  vehicleType?: string;
  scenicCount?: number;
  hotelCount?: number;
  hasToll?: boolean;
}): CostBreakdown {
  const { totalDistance, days, adults, children, vehicleType = "SUV", scenicCount = 0, hotelCount = 0, hasToll = true } = args;
  const people = adults + children;
  const driving = calculateSegmentCost(totalDistance, vehicleType, hasToll);
  const hotelNights = hotelCount || Math.max(days - 1, 0);
  const hotelCost = hotelNights * HOTEL_PER_NIGHT;
  const mealCost = days * 3 * (adults + children * 0.5) * MEAL_PER_PERSON;
  const ticketCost = scenicCount * people * SCENIC_TICKET;
  const total = driving.fuel_cost + driving.toll_cost + hotelCost + mealCost + ticketCost;

  return {
    fuel: driving.fuel_cost,
    toll: driving.toll_cost,
    hotel: r1(hotelCost),
    meal: r1(mealCost),
    ticket: r1(ticketCost),
    total: r1(total),
    breakdown: {
      油费: `¥${driving.fuel_cost.toFixed(0)}`,
      过路费: `¥${driving.toll_cost.toFixed(0)}`,
      住宿: `¥${hotelCost.toFixed(0)}`,
      餐饮: `¥${mealCost.toFixed(0)}`,
      门票: `¥${ticketCost.toFixed(0)}`,
      总计: `¥${total.toFixed(0)}`,
    },
  };
}

function r1(n: number): number {
  return Math.round(n * 10) / 10;
}
