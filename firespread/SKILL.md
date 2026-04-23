# FireSpread
## Applicable Scenarios
- Manages regions on a map.
- Uses SplineMesh to create vertical walls and decals.
- Supports both geodetic and Cartesian coordinates.

## Tech Stack
- Cesium for geospatial calculations (if needed).
- UE5's USplineComponent and UDecalComponent for rendering.

## Implementation
### Manager Class
```cpp
class AFireSpreadActor : public AActor
{
public:
    // Constructor
    AFireSpreadActor()
    {
        PrimaryActorTick.bCanEverTick = true;
    }

    // Blueprint function to add a region
    UFUNCTION(BlueprintCallable)
    void AddRegion(FGeoCoordinate Coordinates, FLinearColor Color);

    // Blueprint function to remove a region
    UFUNCTION(BlueprintCallable)
    void RemoveRegion(AFireSpreadRegionActor* RegionActor);

    // Blueprint function to update the color of a region
    UFUNCTION(BlueprintCallable)
    void UpdateRegionColor(AFireSpreadRegionActor* RegionActor, FLinearColor Color);

    // Function to clear all regions
    UFUNCTION(BlueprintCallable)
    void ClearAllRegions();

private:
    // Array to store region actors
    TArray<AFireSpreadRegionActor*> Regions;

    // Function to generate regions based on input data
    void GenerateRegions(const TArray<FZoneRegionConfig>& RegionConfigs);
};
```
### Region Actor Class
```cpp
class AFireSpreadRegionActor : public AActor
{
public:
    // Constructor
    AFireSpreadRegionActor()
    {
        PrimaryActorTick.bCanEverTick = true;
    }

    // Function to set the material of the decal
    UFUNCTION(BlueprintCallable)
    void SetDecalMaterial(UMaterialInterface* Material);

private:
    // USplineComponent for creating the vertical wall
    USplineComponent* WallSpline;

    // UDecalComponent for the region fill
    UDecalComponent* RegionDecal;

    // Function to update the decal material based on color
    void UpdateDecalMaterial(FLinearColor Color);
};
```
### ZoneRegionConfig Struct
```cpp
struct FZoneRegionConfig
{
    TArray<FGeoCoordinate> Vertices;  // Array of vertices in geodetic coordinates
    FLinearColor Color;            // Fill color for the region
    ECoordinateType CoordinateType;   // Geodetic or Cartesian coordinate type
};
```
### CoordinateConverterBPLibrary Class
```cpp
class UCoordinateConverterBPLibrary : public UObject
{
public:
    // Function to convert geodetic coordinates to UE world coordinates
    static FVector GeodeticToWorld(const FGeoCoordinate& GeoCoord);

    // Function to convert UE world coordinates to geodetic coordinates
    static FGeoCoordinate WorldToGeodetic(const FVector& WorldCoord);
};
```
## Notes
- The module supports both geodetic and Cartesian coordinate systems.
- SplineMesh is used to create vertical walls, and decals are used for region fill.
- The wall height is fixed at 10 meters.
- The decal material can be customized by the user.
- The module automatically adds points to the spline to fit terrain variations.