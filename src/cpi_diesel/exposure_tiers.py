"""How diesel reaches each category of the CPI basket.

This is the editorial core of the project and the file a skeptical reader
should argue with first. Every one of the 81 mutually exclusive expenditure
categories gets exactly one tier and one plain-English sentence explaining the
mechanism. Nothing defaults; build.py fails if a category is unassigned.

The weights are BLS's. The tiers and narratives are ours -- an editorial
overlay on published data, not a BLS aggregate. Say so wherever the numbers
appear.

`intensity` is a deliberately rough estimate of diesel's share of an item's
delivered cost, used only for the secondary "embedded cost" statistic. It is
an order-of-magnitude judgment, not a measurement. Reach is the claim this
project makes with confidence; intensity is included to keep the reach number
from being mistaken for a magnitude number.
"""
from __future__ import annotations

from typing import Dict, NamedTuple


class Tier(NamedTuple):
    key: str
    label: str
    blurb: str
    diesel: bool  # counts toward the "touched by diesel" total


TIERS = {t.key: t for t in [
    Tier("direct_diesel", "Diesel, bought directly",
         "The household buys diesel or the distillate next to it on the barrel.",
         True),
    Tier("diesel_service", "Delivered by a diesel vehicle",
         "A service whose whole delivery mechanism is a diesel engine.",
         True),
    # Not all of it is refrigerated -- roughly half a grocery bill is
    # shelf-stable and rides an ordinary dry van. Both run on diesel, so the
    # tier is named for the turnover rather than the temperature.
    Tier("cold_chain", "Grocery freight",
         "The fastest-turning goods in the basket, restocked several times a "
         "week.",
         True),
    Tier("heavy_freight", "Heavy freight",
         "Bulky, low value-density goods where moving them is a large share of what they cost.",
         True),
    Tier("light_freight", "Light freight",
         "Trucked, but valuable enough per pound that freight is a small share of the price.",
         True),
    Tier("freight_dependent_service", "Service that runs on trucked inputs",
         "The labor is local, but the supplies arrive by truck on a daily cadence.",
         True),
    Tier("gasoline_direct", "Gasoline, bought directly",
         "The comparison anchor: gasoline as a final good households buy.",
         False),
    Tier("other_fuel", "Other fuel, not diesel",
         "Genuinely fuel-exposed, but to jet fuel, natural gas or coal.",
         False),
    Tier("none", "No meaningful diesel content",
         "Nothing physical is delivered, so no freight is consumed.",
         False),
]}


class Assignment(NamedTuple):
    tier: str
    intensity: float
    narrative: str


A = Assignment

# Keyed by the BLS item name exactly as published in Table 1.
EXPOSURE: Dict[str, Assignment] = {

    # ---- Food and beverages ------------------------------------------------
    "Food at home": A(
        "cold_chain", 0.07,
        "Nearly everything in a grocery store arrives on a diesel truck, most "
        "of it more than once a week. Produce, meat, dairy and dry goods all "
        "move farm to processor to distribution center to store, and every leg "
        "burns diesel. This is the clearest case in the whole basket: when "
        "diesel moves, grocery prices follow."),
    "Food away from home": A(
        "freight_dependent_service", 0.03,
        "Restaurant inputs arrive by truck. A typical kitchen takes deliveries "
        "of produce, meat, dry goods and beverages several times a week from "
        "diesel distribution fleets, and the menu price carries that freight "
        "even though the diner never sees a line item for it."),
    "Alcoholic beverages away from home": A(
        "freight_dependent_service", 0.02,
        "Beer, wine and spirits reach bars and restaurants through a three-tier "
        "distribution system that is entirely truck-based. Liquid is heavy and "
        "cheap per pound, so freight is a bigger share of its delivered cost "
        "than most people would guess."),
    "Alcoholic beverages at home": A(
        "heavy_freight", 0.05,
        "Bottled and canned drinks are some of the densest freight in retail. "
        "Distributors run dedicated diesel routes to every store, and the "
        "weight-to-value ratio means a fuel move reaches the shelf price faster "
        "than it does for lighter goods."),

    # ---- Housing -----------------------------------------------------------
    "Owners' equivalent rent of residences": A(
        "none", 0.0,
        "The rent an owner would pay to rent their own home from themselves. "
        "Nothing is manufactured, nothing is delivered, no freight is consumed. "
        "At more than a quarter of the index on its own, this is the largest "
        "genuinely diesel-free category in the CPI -- and a big part of why the "
        "diesel-exposed share tops out where it does."),
    "Rent of primary residence": A(
        "none", 0.0,
        "A monthly payment for space that already exists. Repairs carry a "
        "little embedded freight, but rent itself is a claim on land and "
        "structure, not on anything that has to be moved."),
    "Energy services": A(
        "other_fuel", 0.01,
        "Electricity and piped natural gas, delivered by wire and pipeline "
        "rather than by truck. The fuel exposure is real but it runs to natural "
        "gas and coal, not diesel, so it is kept out of the diesel total on "
        "purpose."),
    "Lodging away from home": A(
        "freight_dependent_service", 0.02,
        "Hotels consume trucked goods continuously -- linens, food, cleaning "
        "supplies, amenities -- on a resupply cadence closer to a restaurant's "
        "than an office's."),
    "Water and sewer and trash collection services": A(
        "diesel_service", 0.10,
        "Refuse collection is one of the most diesel-intensive services a "
        "household buys. Garbage trucks are heavy, stop every few hundred feet, "
        "idle while they load, and post some of the worst fuel economy of any "
        "vehicle class on the road."),
    "Furniture and bedding": A(
        "heavy_freight", 0.06,
        "Bulky, heavy and awkward to pack, furniture is close to a worst case "
        "for freight economics: it fills a trailer by volume long before it "
        "fills it by weight, then often takes a second diesel leg for delivery "
        "into the house."),
    "Household operations": A(
        "freight_dependent_service", 0.02,
        "Housekeeping, gardening, moving and storage. Moving is diesel from end "
        "to end, and the lawn and garden trades tow equipment to every job."),
    "Housekeeping supplies": A(
        "light_freight", 0.03,
        "Detergents, paper goods and cleaners are heavy and cheap per pound. "
        "Water and wood pulp travel a long way by truck before anyone buys "
        "them."),
    "Tools, hardware, outdoor equipment and supplies": A(
        "heavy_freight", 0.05,
        "Lumber, fasteners, paint, mowers and grills. Home-center inventory is "
        "dense, heavy and restocked constantly by dedicated fleets running out "
        "of regional distribution centers."),
    "Other household equipment and furnishings": A(
        "heavy_freight", 0.04,
        "Cookware, dishes, lamps and decor, trucked from port or plant to "
        "distribution center to store. Breakage risk keeps it on roads rather "
        "than cheaper modes."),
    "Tenants' and household insurance": A(
        "none", 0.0,
        "A financial contract. Premiums move with claims experience and "
        "interest rates, not with the cost of moving anything."),
    "Window and floor coverings and other linens": A(
        "light_freight", 0.03,
        "Textiles and floor coverings, mostly imported and then trucked inland "
        "from the port. Rolled carpet in particular is heavy, bulky freight."),
    "Appliances": A(
        "heavy_freight", 0.06,
        "Refrigerators, washers and ranges are the textbook definition of heavy "
        "freight: high weight, high volume, few units per trailer, and usually a "
        "second diesel leg for delivery and installation."),
    "Fuel oil and other fuels": A(
        "direct_diesel", 0.90,
        "Home heating oil is essentially diesel. It comes off the same "
        "distillate cut of the barrel, competes for the same refinery output, "
        "and arrives at the house on a diesel tanker truck. When diesel moves, "
        "this moves with it almost one for one."),

    # ---- Apparel -----------------------------------------------------------
    "Women's apparel": A(
        "light_freight", 0.02,
        "Overwhelmingly imported, then trucked from port to distribution center "
        "to store or doorstep. Clothing is light for its value, so freight is a "
        "small share of the price -- but it is never zero, and e-commerce has "
        "added diesel legs to garments that used to make only one trip."),
    "Men's apparel": A(
        "light_freight", 0.02,
        "The same import-and-truck path as the rest of apparel: container to "
        "port, a short diesel drayage move to a distribution center, then "
        "line-haul to wherever it is sold."),
    "Women's footwear": A(
        "light_freight", 0.02,
        "Shoes ship in boxes that waste a lot of trailer space for their "
        "weight, which pushes freight cost per pair above what the materials "
        "alone would suggest."),
    "Men's footwear": A(
        "light_freight", 0.02,
        "Boxed, bulky for its weight, and moved through the same port-to-"
        "distribution-center truck network as the rest of footwear."),
    "Girls' apparel": A(
        "light_freight", 0.02,
        "Imported and trucked inland. Small garments, small freight share, but "
        "the same road network underneath."),
    "Jewelry": A(
        "light_freight", 0.005,
        "Almost pure value with almost no weight. Jewelry tends to move by "
        "air and secure courier rather than freight truck, making it one of the "
        "least diesel-exposed physical goods in the basket."),
    "Boys' and girls' footwear": A(
        "light_freight", 0.02,
        "The same boxed, low-density freight profile as adult footwear, on the "
        "same truck routes — a lot of trailer space for very little weight."),
    "Boys' apparel": A(
        "light_freight", 0.02,
        "Imported, containerized, then trucked to store or doorstep. Small "
        "garments make the same three road moves as large ones."),
    "Infants' and toddlers' apparel": A(
        "light_freight", 0.02,
        "Light goods on the standard import-and-truck path; freight is a small "
        "but real slice of the price."),
    "Watches": A(
        "light_freight", 0.005,
        "High value, negligible weight, and frequently air-freighted. Along "
        "with jewelry, this is about as close to diesel-free as a physical "
        "good in the basket gets."),

    # ---- Transportation ----------------------------------------------------
    "New and used motor vehicles": A(
        "heavy_freight", 0.03,
        "A finished car weighs two tons and travels by rail and specialised "
        "diesel car-hauler, usually both. Its parts made several diesel trips "
        "before assembly and it makes at least one more to the dealer lot. At "
        "7.2% of the index this is the largest freight-exposed category outside "
        "food."),
    "Gasoline (all types)": A(
        "gasoline_direct", 0.0,
        "The comparison anchor. This is gasoline households pump themselves, "
        "and it is essentially gasoline's entire role in the CPI: 2.895% of the "
        "index, the number that gets all the attention. Gasoline is a final "
        "good here, not an input cost hidden inside anything else in the "
        "basket."),
    "Motor vehicle insurance": A(
        "none", 0.0,
        "A financial product. Premiums track crash frequency, repair costs and "
        "litigation. The repairs carry a little freight; the insurance itself "
        "burns nothing."),
    "Motor vehicle maintenance and repair": A(
        "freight_dependent_service", 0.02,
        "Every part on a shop's shelf got there by truck, and the parts "
        "distribution network runs several deliveries a day to keep the bays "
        "moving."),
    "Airline fares": A(
        "other_fuel", 0.0,
        "Jet fuel is diesel's close cousin. Both are drawn from the same middle "
        "distillate cut of the barrel, and they move together closely enough to "
        "measure: month to month their prices track at 0.90, and still at 0.72 "
        "once you strip out the crude oil that every fuel follows — against "
        "0.21 for gasoline. Fuel is roughly a fifth of what it costs to run an "
        "airline, so when the distillate market moves, fares follow it rather "
        "than the pump price. It sits outside the total here only because the "
        "number on this page is about diesel specifically; counting its cousin "
        "would take it to 45.3%."),
    "Motor vehicle fees": A(
        "none", 0.0,
        "Registration, licensing and parking. Administrative and municipal "
        "charges set by policy, not by the cost of goods."),
    "Intracity transportation": A(
        "diesel_service", 0.15,
        "City buses. Transit fleets remain substantially diesel and "
        "diesel-hybrid, and fuel is one of the largest controllable line items "
        "in an agency's operating budget."),
    "Motor vehicle parts and equipment": A(
        "heavy_freight", 0.04,
        "Tires dominate this category, and they are a freight planner's "
        "problem: heavy, bulky, and impossible to stack efficiently."),
    "Other intercity transportation": A(
        "diesel_service", 0.15,
        "Intercity buses, rail and ferries. Motorcoaches run on diesel, "
        "locomotives run on diesel-electric drives, and ferries burn marine "
        "distillate."),
    "Other motor fuels": A(
        "direct_diesel", 0.95,
        "This is where consumer diesel actually sits in the CPI: 0.086% of the "
        "index, thirty-four times smaller than gasoline. That number is the "
        "whole reason diesel gets ignored -- and it counts only the diesel "
        "households pump themselves. It says nothing about the diesel burned to "
        "deliver everything else they buy."),
    "Unsampled public transportation": A(
        "diesel_service", 0.10,
        "A residual line BLS carries so public transportation sums correctly. "
        "Treated with the rest of surface transit."),

    # ---- Medical care ------------------------------------------------------
    "Professional services": A(
        "freight_dependent_service", 0.01,
        "Physician, dental and eye care. The labor is local, but the "
        "consumables -- gloves, reagents, instruments, drugs -- arrive on a "
        "daily medical-supply route."),
    "Hospital and related services": A(
        "freight_dependent_service", 0.015,
        "Hospitals run on continuous resupply: sterile goods, drugs, linens, "
        "food service, medical gases and waste hauling. A hospital loading dock "
        "is busier than most warehouses."),
    "Medicinal drugs": A(
        "light_freight", 0.015,
        "Pharmaceuticals are light and valuable, but they move through a "
        "tightly controlled, often temperature-controlled network of frequent, "
        "small, time-definite truck deliveries to every pharmacy in the "
        "country."),
    "Health insurance": A(
        "none", 0.0,
        "As the CPI measures it, this is the retained earnings of health "
        "insurers rather than a physical product. No freight content at all."),
    "Medical equipment and supplies": A(
        "light_freight", 0.02,
        "Wheelchairs, walkers, monitors and supplies, shipped from national "
        "distributors to pharmacies, clinics and homes."),

    # ---- Recreation --------------------------------------------------------
    "Club membership for shopping clubs, fraternal, or other organizations, or participant sports fees": A(
        "none", 0.0,
        "Gym, warehouse-club and organization dues. This is a fee for the right "
        "to walk in the door, not for anything delivered — the goods a "
        "warehouse club sells are priced in the food and household categories "
        "instead."),
    "Admissions": A(
        "none", 0.0,
        "Tickets to films, concerts and games, priced on venue capacity and "
        "demand. No freight content."),
    "Pets and pet products": A(
        "heavy_freight", 0.06,
        "Pet food is the story here — dry kibble by the sack, on ordinary dry "
        "vans. It is heavy, cheap per pound and bought in bulk, which gives it "
        "one of the highest ratios of freight cost to retail price of any "
        "consumer good."),
    "Cable, satellite, and live streaming television service": A(
        "none", 0.0,
        "Delivered over cable, satellite and broadband. Once the wire is in the "
        "ground nothing physical moves, so there is no freight in the monthly "
        "bill at all."),
    "Pet services including veterinary": A(
        "freight_dependent_service", 0.015,
        "Veterinary practices take the same daily supply deliveries as human "
        "clinics: drugs, consumables, lab reagents."),
    "Toys": A(
        "light_freight", 0.03,
        "Almost entirely imported and notoriously bulky for their weight, which "
        "makes toys expensive to move relative to what they cost to make."),
    "Sports vehicles including bicycles": A(
        "heavy_freight", 0.05,
        "Bicycles, boats and off-road vehicles: large, heavy, and shipped part-"
        "assembled in packaging that eats trailer space."),
    "Sports equipment": A(
        "light_freight", 0.03,
        "Bats, weights and camping gear fill a trailer's volume long before "
        "they reach its weight limit."),
    "Unsampled recreation services": A(
        "none", 0.0,
        "A BLS residual for recreation services not separately priced. No "
        "specific freight mechanism to attribute."),
    "Purchase, subscription, and rental of video": A(
        "none", 0.0,
        "Once discs shipped in cases by the millions; now this is overwhelmingly "
        "streaming, delivered over the internet. One of the few categories "
        "where diesel exposure has genuinely fallen to near zero over time."),
    "Fees for lessons or instructions": A(
        "none", 0.0,
        "Music, driving and tutoring lessons. Paying for a person's time and "
        "expertise in a room that already exists — nothing is manufactured and "
        "nothing is shipped."),
    "Televisions": A(
        "light_freight", 0.03,
        "Large, fragile and low-density. A television takes far more trailer "
        "space than its weight suggests, and its fragility keeps it on trucks "
        "rather than cheaper modes."),
    "Recorded music and music subscriptions": A(
        "none", 0.0,
        "Effectively all streaming now, delivered as bits. The vinyl revival is "
        "real but far too small to put meaningful freight back into this "
        "category."),
    "Recreational books": A(
        "light_freight", 0.04,
        "Paper is heavy. Books have one of the worst weight-to-value ratios in "
        "retail, which is exactly why the industry consolidated into a handful "
        "of enormous distribution centers served by dedicated truck fleets."),
    "Newspapers and magazines": A(
        "light_freight", 0.04,
        "What is left of print still moves by truck against a daily deadline, "
        "which is about as freight-sensitive as delivery gets."),
    "Audio equipment": A(
        "light_freight", 0.02,
        "Speakers and headphones, imported and boxed. Speakers in particular "
        "carry heavy magnets and cabinets, so they cost more to move than their "
        "size suggests."),
    "Music instruments and accessories": A(
        "light_freight", 0.03,
        "Instruments are fragile and oddly shaped, which rules out dense "
        "packing and keeps them on carefully handled truck freight."),
    "Photographers and photo processing": A(
        "none", 0.0,
        "A service priced on a photographer's time. Processing that once meant "
        "shipping film and prints is now almost entirely digital."),
    "Sewing machines, fabric and supplies": A(
        "light_freight", 0.03,
        "Bolts of fabric are dense and heavy, and machines are boxed and awkward "
        "to stack. Both are trucked, and neither packs efficiently."),
    "Photographic equipment and supplies": A(
        "light_freight", 0.01,
        "Cameras and lenses are small, valuable and often air-freighted, so they "
        "spend little time on a truck relative to what they cost."),
    "Other video equipment": A(
        "light_freight", 0.02,
        "Streaming boxes, projectors and accessories — light, boxed electronics "
        "on the standard port-to-warehouse-to-store road network."),
    "Unsampled recreation commodities": A(
        "light_freight", 0.02,
        "A BLS residual covering recreation goods not separately priced. They "
        "are physical goods, so they ride the same trucks."),
    "Unsampled sporting goods": A(
        "light_freight", 0.03,
        "A BLS residual for sporting goods not separately priced. Bulky for "
        "their weight, like the rest of the category, so they ride the same "
        "trucks."),
    "Unsampled video and audio": A(
        "light_freight", 0.02,
        "A BLS residual for video and audio goods not separately priced. They "
        "are physical, boxed electronics, so they move on the same import and "
        "distribution routes as the rest."),
    "Unsampled photography": A(
        "light_freight", 0.01,
        "A BLS residual for photography not separately priced. It carries "
        "essentially no weight in the index, but it is grouped with the goods "
        "rather than the services."),
    "Unsampled recreational reading materials": A(
        "light_freight", 0.04,
        "A BLS residual for reading material not separately priced. Printed "
        "matter is heavy paper on the same truck network as books and "
        "magazines."),

    # ---- Education and communication ---------------------------------------
    "Information and information processing": A(
        "none", 0.0,
        "Wireless and residential phone service, internet access, and the "
        "computer hardware that goes with them. The services travel over "
        "networks and the hardware is light, valuable and often air-freighted. "
        "At 3.2% of the index this is a large, essentially diesel-free block."),
    "Tuition, other school fees, and childcare": A(
        "none", 0.0,
        "Salaries, facilities and administration. Schools do take deliveries, "
        "but tuition is priced on staffing and enrollment, not on what arrives "
        "at the loading dock."),
    "Postage and delivery services": A(
        "diesel_service", 0.12,
        "Parcel and mail delivery, priced directly. Every package moves through "
        "diesel line-haul between sorting hubs before it reaches a local van. "
        "This is one of the few places in the CPI where households pay for "
        "freight explicitly instead of having it buried inside a product "
        "price."),
    "Educational books and supplies": A(
        "light_freight", 0.04,
        "Textbooks are heavy paper shipped against a hard seasonal deadline, "
        "which is the expensive way to move freight — the trucks have to run "
        "whether or not they are full."),

    # ---- Other goods and services ------------------------------------------
    "Miscellaneous personal services": A(
        "none", 0.0,
        "Legal, financial and funeral services, priced on professional time and "
        "billed by the hour. Nothing here moves on a road."),
    "Personal care services": A(
        "none", 0.0,
        "Haircuts, salons and spas — labor sold by the appointment. The products "
        "on the shelf behind the chair are counted under personal care products "
        "instead."),
    "Personal care products": A(
        "light_freight", 0.03,
        "Shampoo, soap and cosmetics are mostly water by weight, shipped in "
        "heavy liquid form to every drugstore and big-box shelf in the "
        "country."),
    "Cigarettes": A(
        "light_freight", 0.02,
        "Light, valuable, and moved on secure, frequent truck routes to "
        "convenience stores. Freight is a small share of a price dominated by "
        "excise tax."),
    "Miscellaneous personal goods": A(
        "light_freight", 0.02,
        "Luggage, handbags and small personal items. Almost entirely imported, "
        "and luggage in particular is mostly air inside a shell, so it burns "
        "trailer space rather than payload."),
    "Tobacco products other than cigarettes": A(
        "light_freight", 0.02,
        "Cigars, pipe and smokeless tobacco, moving on the same secure, frequent "
        "truck routes to convenience stores as cigarettes."),
    "Unsampled tobacco and smoking products": A(
        "light_freight", 0.02,
        "A BLS residual for tobacco products not separately priced. It follows "
        "the same convenience-store delivery network as the rest of the "
        "category."),
}


def lookup(name: str) -> Assignment:
    try:
        return EXPOSURE[name]
    except KeyError:
        raise KeyError(
            f"no diesel-exposure assignment for CPI category {name!r}. Add one "
            f"to exposure_tiers.EXPOSURE -- there are no silent defaults."
        ) from None
